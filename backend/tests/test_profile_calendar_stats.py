"""Records, time of day and weekday of Mon profil, on the clock of the saved zone."""
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import update

from models.playback_stats import PlaybackSession
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.portal import profile_stats
from services.portal.profile_stats_playback import compute_calendar_stats
from services.settings import set_setting
from tests._portal_profile_helpers import make_portal_user

PARIS = ZoneInfo("Europe/Paris")
PLAYER = PlaybackSession.user_name == "alice"
LOGGER = "mediakeeper.portal.profile_stats"


def _add(db, started: datetime, *, user: str = "alice", item: str = "item-1") -> None:
    db.add(PlaybackSession(
        session_key=f"{user}-{item}-{started.timestamp()}-{len(db.new)}",
        user_id=f"emby-{user}",
        user_name=user,
        item_id=item,
        item_name="Test Movie",
        item_type="Movie",
        started_at=started,
        last_seen_at=started,
        ended_at=started + timedelta(minutes=1),
    ))


async def _stats(db, zone, *starts: datetime, excl: list | None = None) -> dict:
    for started in starts:
        _add(db, started)
    await db.commit()
    return await compute_calendar_stats(db, PLAYER, excl or [], zone)


def _weekdays(stats: dict) -> dict[int, int]:
    return {row["day"]: row["count"] for row in stats["day_stats"] if row["count"]}


def _buckets(stats: dict) -> dict[str, int]:
    return {row["bucket"]: row["count"] for row in stats["hour_buckets"] if row["count"]}


@pytest.mark.asyncio
async def test_a_play_after_midnight_belongs_to_the_next_local_day(db_session):
    """Wednesday 22:30 UTC is 00:30 on Thursday in Paris."""
    late = datetime(2026, 10, 14, 22, 30, tzinfo=UTC)
    noon = datetime(2026, 10, 14, 12, tzinfo=UTC)
    in_utc = await _stats(db_session, UTC, late, late, late, noon, noon)
    in_paris = await compute_calendar_stats(db_session, PLAYER, [], PARIS)

    assert in_utc["record_day"] == {"date": "2026-10-14", "count": 5}
    assert in_paris["record_day"] == {"date": "2026-10-15", "count": 3}
    assert _weekdays(in_utc) == {2: 5}
    assert _weekdays(in_paris) == {2: 2, 3: 3}


@pytest.mark.asyncio
async def test_a_play_after_midnight_belongs_to_the_next_local_month(db_session):
    late = datetime(2026, 10, 31, 23, 30, tzinfo=UTC)
    mid = datetime(2026, 10, 15, 12, tzinfo=UTC)
    in_utc = await _stats(db_session, UTC, late, late, late, mid, mid)
    in_paris = await compute_calendar_stats(db_session, PLAYER, [], PARIS)

    assert in_utc["record_month"] == {"month": "2026-10", "count": 5}
    assert in_paris["record_month"] == {"month": "2026-11", "count": 3}


@pytest.mark.asyncio
@pytest.mark.parametrize(("started", "date"), [
    # Two hours ahead in summer, one in winter: the same UTC time lands on another day.
    (datetime(2026, 7, 14, 22, 30, tzinfo=UTC), "2026-07-15"),
    (datetime(2026, 1, 14, 22, 30, tzinfo=UTC), "2026-01-14"),
])
async def test_the_offset_of_the_day_itself_counts(db_session, started, date):
    stats = await _stats(db_session, PARIS, started)

    assert stats["record_day"]["date"] == date


@pytest.mark.asyncio
@pytest.mark.parametrize(("hour", "minute", "bucket"), [
    (0, 0, "night"),
    (5, 59, "night"),
    (6, 0, "morning"),
    (11, 59, "morning"),
    (12, 0, "afternoon"),
    (17, 59, "afternoon"),
    (18, 0, "evening"),
    (22, 59, "evening"),
    (23, 0, "night"),
])
async def test_time_of_day_limits_on_the_local_clock(db_session, hour, minute, bucket):
    local = datetime(2026, 1, 15, hour, minute, tzinfo=PARIS)

    stats = await _stats(db_session, PARIS, local.astimezone(UTC))

    assert _buckets(stats) == {bucket: 1}


@pytest.mark.asyncio
async def test_weekdays_run_from_monday_to_sunday(db_session):
    monday = datetime(2026, 11, 2, 12, tzinfo=UTC)
    sunday = datetime(2026, 11, 8, 12, tzinfo=UTC)

    stats = await _stats(db_session, UTC, monday, sunday, sunday)

    assert [row["day"] for row in stats["day_stats"]] == list(range(7))
    assert _weekdays(stats) == {0: 1, 6: 2}


@pytest.mark.asyncio
async def test_a_tie_keeps_the_earliest_record_whatever_the_order_of_the_rows(db_session):
    stats = await _stats(
        db_session, UTC,
        datetime(2026, 11, 20, 12, tzinfo=UTC),
        datetime(2026, 3, 10, 12, tzinfo=UTC),
        datetime(2026, 7, 5, 12, tzinfo=UTC),
    )

    assert stats["record_day"] == {"date": "2026-03-10", "count": 1}
    assert stats["record_month"] == {"month": "2026-03", "count": 1}


@pytest.mark.asyncio
async def test_more_plays_beat_an_earlier_day(db_session):
    early = datetime(2026, 3, 10, 12, tzinfo=UTC)
    later = datetime(2026, 7, 5, 12, tzinfo=UTC)

    stats = await _stats(db_session, UTC, early, later, later)

    assert stats["record_day"] == {"date": "2026-07-05", "count": 2}
    assert stats["record_month"] == {"month": "2026-07", "count": 2}


@pytest.mark.asyncio
async def test_no_play_shows_empty_records_and_a_full_week(db_session):
    stats = await compute_calendar_stats(db_session, PLAYER, [], PARIS)

    assert stats == {
        "record_day": {"date": None, "count": 0},
        "record_month": {"month": None, "count": 0},
        "hour_buckets": [
            {"bucket": "morning", "count": 0},
            {"bucket": "afternoon", "count": 0},
            {"bucket": "evening", "count": 0},
            {"bucket": "night", "count": 0},
        ],
        "day_stats": [{"day": day, "count": 0} for day in range(7)],
    }


@pytest.mark.asyncio
async def test_other_players_and_excluded_titles_are_left_out(db_session):
    started = datetime(2026, 10, 14, 12, tzinfo=UTC)
    _add(db_session, started, user="bob")
    _add(db_session, started, item="theme-song")

    stats = await _stats(
        db_session, UTC, started, excl=[PlaybackSession.item_id != "theme-song"],
    )

    assert stats["record_day"] == {"date": "2026-10-14", "count": 1}
    assert _buckets(stats) == {"afternoon": 1}
    assert _weekdays(stats) == {2: 1}


@pytest.mark.asyncio
async def test_a_row_without_a_date_counts_nowhere(db_session):
    started = datetime(2026, 10, 14, 12, tzinfo=UTC)
    _add(db_session, started)
    _add(db_session, started, item="no-date")
    await db_session.commit()
    await db_session.execute(
        update(PlaybackSession).where(PlaybackSession.item_id == "no-date").values(started_at=None)
    )
    await db_session.commit()

    stats = await compute_calendar_stats(db_session, PLAYER, [], PARIS)

    assert stats["record_day"] == {"date": "2026-10-14", "count": 1}
    assert sum(_buckets(stats).values()) == 1


@pytest.mark.asyncio
async def test_a_date_at_the_edge_of_the_calendar_breaks_nothing(db_session):
    stats = await _stats(
        db_session, ZoneInfo("America/New_York"),
        datetime(1, 1, 1, tzinfo=UTC),
        datetime(2026, 10, 14, 12, tzinfo=UTC),
        datetime(2026, 10, 14, 13, tzinfo=UTC),
    )

    assert stats["record_day"] == {"date": "2026-10-14", "count": 2}
    assert stats["record_month"] == {"month": "2026-10", "count": 2}


@pytest.mark.asyncio
async def test_a_failed_read_is_logged_and_shows_empty_stats(db_session, monkeypatch, caplog):
    monkeypatch.setattr(db_session, "execute", AsyncMock(side_effect=RuntimeError("Test error")))

    with caplog.at_level(logging.INFO, logger=LOGGER):
        stats = await compute_calendar_stats(db_session, PLAYER, [], PARIS)

    assert stats["record_day"] == {"date": None, "count": 0}
    assert stats["record_month"] == {"month": None, "count": 0}
    assert sum(row["count"] for row in stats["hour_buckets"]) == 0
    assert stats["day_stats"] is None
    assert [(r.levelname, r.getMessage()) for r in caplog.records if r.name == LOGGER] == [
        ("ERROR", "[PROFILE] calendar stats failed: Test error"),
    ]


@pytest.mark.asyncio
async def test_mon_profil_shows_the_stats_of_the_saved_zone(db_session):
    user, profile = await make_portal_user(db_session, username="alice", emby_user_id="emby-alice")
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    _add(db_session, datetime(2026, 10, 31, 23, 30, tzinfo=UTC))
    await db_session.commit()
    empty = AsyncMock(return_value=[])

    with patch.multiple(
        profile_stats,
        compute_most_rewatched=AsyncMock(return_value=(None, None, None)),
        compute_genre_stats=empty,
        fetch_recent_watches=empty,
        fetch_next_to_finish=empty,
        fetch_my_requests=empty,
    ):
        out = await profile_stats.get_profile_full(db_session, user, profile)

    stats = out["stats"]
    assert stats["record_day"] == {"date": "2026-11-01", "count": 1}
    assert stats["record_month"] == {"month": "2026-11", "count": 1}
    assert _buckets(stats) == {"night": 1}
    # 1 November 2026 is a Sunday in Paris; 31 October, in UTC, a Saturday.
    assert _weekdays(stats) == {6: 1}
