"""The records, the streaks and the user card of the statistics, in the saved zone."""
import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import update

from models.playback_stats import PlaybackSession
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.settings import set_setting
from services.stats_aggregator.charts import get_daily_chart_data
from services.stats_aggregator.profile import get_user_profile
from services.stats_aggregator.records import get_records
from tests._stats_local_time_helpers import freeze, play, save_paris, utc

# Enough watching to fill a day of the streak on its own.
WATCHED_DAY = 10 * 60


def _watch(db, started: datetime, **fields) -> None:
    play(db, started, watched=WATCHED_DAY, exclusive=WATCHED_DAY, **fields)


@pytest.mark.asyncio
async def test_the_record_day_and_the_peak_hour_follow_the_zone(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    for _ in range(3):
        play(db_session, utc(2026, 10, 14, 22, 30))
    for _ in range(2):
        play(db_session, utc(2026, 10, 14, 12))
    await db_session.commit()

    in_utc = await get_records(db_session)
    await save_paris(db_session)
    in_paris = await get_records(db_session)

    assert (in_utc["record_day_date"], in_utc["record_day_count"]) == ("2026-10-14", 5)
    assert (in_utc["peak_hour"], in_utc["peak_hour_count"]) == (22, 3)
    assert (in_paris["record_day_date"], in_paris["record_day_count"]) == ("2026-10-15", 3)
    # Midnight is an hour like any other, though zero reads as false.
    assert (in_paris["peak_hour"], in_paris["peak_hour_count"]) == (0, 3)


@pytest.mark.asyncio
async def test_a_tie_keeps_the_earliest_record_and_the_earliest_hour(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    play(db_session, utc(2026, 10, 14, 20))
    play(db_session, utc(2026, 10, 3, 9))
    await db_session.commit()

    stats = await get_records(db_session)

    assert stats["record_day_date"] == "2026-10-03"
    assert stats["peak_hour"] == 9


@pytest.mark.asyncio
@pytest.mark.parametrize(("now", "current"), [
    # Played today.
    (utc(2026, 10, 16, 18), 3),
    # Nothing yet today: the run holds as long as yesterday counts.
    (utc(2026, 10, 17, 9), 3),
    # A whole day without a play: the run is over.
    (utc(2026, 10, 18, 9), 0),
])
async def test_the_streak_holds_until_a_whole_day_is_missed(db_session, monkeypatch, now, current):
    freeze(monkeypatch, now)
    for day in (14, 15, 16):
        _watch(db_session, utc(2026, 10, day, 12))
    await db_session.commit()

    assert (await get_records(db_session))["current_streak"] == current


@pytest.mark.asyncio
async def test_a_day_of_the_streak_needs_five_minutes_from_all_players(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 16, 18))
    play(db_session, utc(2026, 10, 14, 12), watched=120, exclusive=120)
    play(db_session, utc(2026, 10, 15, 12), watched=180, exclusive=180)
    play(db_session, utc(2026, 10, 15, 20), user="bob", watched=180, exclusive=180)
    _watch(db_session, utc(2026, 10, 16, 12))
    await db_session.commit()

    stats = await get_records(db_session)

    assert (stats["current_streak"], stats["longest_streak"]) == (2, 2)


@pytest.mark.asyncio
async def test_the_streaks_follow_the_days_of_the_zone(db_session, monkeypatch):
    """A play at 22:30 UTC fills the next day in Paris: the gap closes there, not in UTC."""
    freeze(monkeypatch, utc(2026, 10, 16, 18))
    _watch(db_session, utc(2026, 10, 14, 22, 30))
    _watch(db_session, utc(2026, 10, 16, 12))
    await db_session.commit()

    in_utc = await get_records(db_session)
    await save_paris(db_session)
    in_paris = await get_records(db_session)

    assert (in_utc["current_streak"], in_utc["longest_streak"]) == (1, 1)
    assert (in_paris["current_streak"], in_paris["longest_streak"]) == (2, 2)


@pytest.mark.asyncio
async def test_a_film_finished_after_midnight_holds_the_streak(db_session, monkeypatch):
    """The 15th only holds the end of a film started at 23:00 in Paris the day before."""
    freeze(monkeypatch, utc(2026, 10, 16, 18))
    _watch(db_session, utc(2026, 10, 14, 12))
    play(db_session, utc(2026, 10, 14, 21), watched=75 * 60, exclusive=75 * 60)
    _watch(db_session, utc(2026, 10, 16, 12))
    await db_session.commit()
    await save_paris(db_session)

    stats = await get_records(db_session)

    assert (stats["current_streak"], stats["longest_streak"]) == (3, 3)
    # The record day still counts the plays started on it.
    assert (stats["record_day_date"], stats["record_day_count"]) == ("2026-10-14", 2)


@pytest.mark.asyncio
async def test_today_of_the_streak_follows_the_zone(db_session, monkeypatch):
    """18:00 UTC on the 16th is the 17th in Auckland: its 16th stayed empty, so the run is over."""
    freeze(monkeypatch, utc(2026, 10, 16, 18))
    # The 14th and the 15th in Auckland.
    _watch(db_session, utc(2026, 10, 13, 12))
    _watch(db_session, utc(2026, 10, 14, 12))
    await db_session.commit()
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Pacific/Auckland")

    stats = await get_records(db_session)

    assert (stats["current_streak"], stats["longest_streak"]) == (0, 2)


@pytest.mark.asyncio
async def test_the_longest_streak_finds_a_past_run(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    for day in (1, 2, 3, 4, 10):
        _watch(db_session, utc(2026, 10, day, 12))
    await db_session.commit()

    stats = await get_records(db_session)

    assert (stats["current_streak"], stats["longest_streak"]) == (0, 4)


@pytest.mark.asyncio
async def test_no_play_gives_empty_records(db_session):
    stats = await get_records(db_session)

    assert stats == {
        "record_day_date": None,
        "record_day_count": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "top_user_name": None,
        "top_user_pct": 0,
        "peak_hour": None,
        "peak_hour_count": 0,
    }


@pytest.mark.asyncio
async def test_records_leave_out_excluded_titles_and_rows_without_a_date(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    await set_setting(
        db_session, "stats.exclusions", json.dumps([{"mode": "exact", "value": "Test Intro"}]),
    )
    _watch(db_session, utc(2026, 10, 14, 12))
    # Without the list, the excluded title would make a run of two days.
    _watch(db_session, utc(2026, 10, 13, 9), item="Test Intro")
    _watch(db_session, utc(2026, 10, 13, 9), item="Test Intro")
    play(db_session, utc(2026, 10, 5, 9), item="No Date")
    await db_session.commit()
    await db_session.execute(
        update(PlaybackSession).where(PlaybackSession.item_name == "No Date").values(started_at=None)
    )
    await db_session.commit()

    stats = await get_records(db_session)

    assert (stats["record_day_date"], stats["record_day_count"]) == ("2026-10-14", 1)
    assert (stats["peak_hour"], stats["peak_hour_count"]) == (12, 1)
    assert stats["longest_streak"] == 1


@pytest.mark.asyncio
async def test_a_date_at_the_edge_of_the_calendar_breaks_no_statistic(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "America/New_York")
    play(db_session, datetime(1, 1, 1, tzinfo=UTC))
    play(db_session, utc(2026, 10, 14, 12))
    play(db_session, utc(2026, 10, 14, 13))
    await db_session.commit()

    assert (await get_records(db_session))["record_day_date"] == "2026-10-14"
    assert (await get_daily_chart_data(db_session, days=30))["data"]["2026-10-14"]["Films"]["count"] == 2


@pytest.mark.asyncio
async def test_the_user_card_counts_its_30_days_on_the_local_calendar(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 31, 23, 30))
    play(db_session, utc(2026, 10, 31, 23, 10))
    play(db_session, utc(2026, 10, 31, 21))
    play(db_session, utc(2026, 10, 31, 21), user="bob")
    play(db_session, utc(2026, 9, 1, 12))
    await db_session.commit()

    in_utc = (await get_user_profile(db_session, "emby-alice"))["daily_activity"]
    await save_paris(db_session)
    in_paris = (await get_user_profile(db_session, "emby-alice"))["daily_activity"]

    assert len(in_utc) == len(in_paris) == 30
    assert (in_utc[0]["date"], in_utc[-1]) == ("2026-10-02", {"date": "2026-10-31", "count": 2})
    assert (in_paris[0]["date"], in_paris[-1]) == ("2026-10-03", {"date": "2026-11-01", "count": 1})
    assert in_paris[-2] == {"date": "2026-10-31", "count": 1}
    assert sum(day["count"] for day in in_paris) == 2


@pytest.mark.asyncio
async def test_the_user_card_leaves_out_excluded_titles(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    await set_setting(
        db_session, "stats.exclusions", json.dumps([{"mode": "exact", "value": "Test Intro"}]),
    )
    play(db_session, utc(2026, 10, 14, 12))
    play(db_session, utc(2026, 10, 14, 13), item="Test Intro")
    await db_session.commit()

    card = await get_user_profile(db_session, "emby-alice")

    assert sum(day["count"] for day in card["daily_activity"]) == 1


@pytest.mark.asyncio
async def test_the_routes_serve_the_saved_zone(authed_client, db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    play(db_session, utc(2026, 10, 14, 22, 30))
    await db_session.commit()
    await save_paris(db_session)

    chart = (await authed_client.get("/api/stats/chart/daily", params={"days": 30})).json()
    heatmap = (await authed_client.get("/api/stats/heatmap", params={"days": 30})).json()
    stats = (await authed_client.get("/api/stats/records")).json()
    card = (await authed_client.get(
        "/api/stats/user_profile", params={"user_id": "emby-alice"},
    )).json()

    assert chart["data"]["2026-10-15"]["Films"]["count"] == 1
    assert heatmap["grid"][4][0] == 1
    assert (stats["record_day_date"], stats["peak_hour"]) == ("2026-10-15", 0)
    assert {"date": "2026-10-15", "count": 1} in card["daily_activity"]
