"""The daily charts and the heatmap of the statistics, on the clock of the saved zone."""
import json

import pytest

from models.playback_stats import LibraryCache
from services.settings import set_setting
from services.stats_aggregator.charts import get_daily_chart_data, get_weekly_heatmap
from tests._stats_local_time_helpers import (
    SECOND_IN_TICKS,
    freeze,
    play,
    save_paris,
    utc,
)


@pytest.mark.asyncio
async def test_a_late_play_moves_to_the_next_local_day_on_the_chart(db_session, monkeypatch):
    """22:30 UTC on 14 October is 00:30 on the 15th in Paris."""
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    play(db_session, utc(2026, 10, 14, 22, 30))
    await db_session.commit()

    in_utc = await get_daily_chart_data(db_session, days=30)
    await save_paris(db_session)
    in_paris = await get_daily_chart_data(db_session, days=30)

    expected = {"Films": {"count": 1, "duration": 60 * SECOND_IN_TICKS}}
    assert in_utc["data"]["2026-10-14"] == expected
    assert in_utc["data"]["2026-10-15"] == {}
    assert in_paris["data"]["2026-10-14"] == {}
    assert in_paris["data"]["2026-10-15"] == expected


@pytest.mark.asyncio
async def test_the_days_of_the_chart_end_on_the_local_today(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 31, 23, 30))

    in_utc = await get_daily_chart_data(db_session, days=2)
    await save_paris(db_session)
    in_paris = await get_daily_chart_data(db_session, days=2)

    assert in_utc["days"] == ["2026-10-29", "2026-10-30", "2026-10-31"]
    assert in_paris["days"] == ["2026-10-30", "2026-10-31", "2026-11-01"]
    assert all(in_paris["data"][day] == {} for day in in_paris["days"])


@pytest.mark.asyncio
async def test_the_chart_adds_up_a_day_and_keeps_each_group_apart(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    day = utc(2026, 10, 14, 12)
    play(db_session, day, watched=10, exclusive=4)
    play(db_session, day, watched=20, exclusive=5)
    play(db_session, day, library="Series", user="bob", watched=30, exclusive=6)
    await db_session.commit()

    by_library = await get_daily_chart_data(db_session, days=30)
    by_user = await get_daily_chart_data(db_session, days=30, group_by="user")

    assert by_library["groups"] == ["Films", "Series"]
    assert by_library["data"]["2026-10-14"] == {
        "Films": {"count": 2, "duration": 30 * SECOND_IN_TICKS},
        "Series": {"count": 1, "duration": 30 * SECOND_IN_TICKS},
    }
    assert by_user["groups"] == ["alice", "bob"]
    assert by_user["data"]["2026-10-14"] == {
        "alice": {"count": 2, "duration": 9 * SECOND_IN_TICKS},
        "bob": {"count": 1, "duration": 6 * SECOND_IN_TICKS},
    }


@pytest.mark.asyncio
async def test_the_chart_merges_two_names_of_one_library(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    db_session.add(LibraryCache(lib_id="1", name="Mangas & Animes"))
    day = utc(2026, 10, 14, 12)
    play(db_session, day, library="mangasetanimes", watched=10)
    play(db_session, day, library="Mangas & Animes", watched=20)
    await db_session.commit()

    chart = await get_daily_chart_data(db_session, days=30)

    assert chart["groups"] == ["Mangas & Animes"]
    assert chart["data"]["2026-10-14"] == {
        "Mangas & Animes": {"count": 2, "duration": 30 * SECOND_IN_TICKS},
    }


@pytest.mark.asyncio
async def test_the_chart_leaves_out_old_plays_excluded_titles_and_rows_without_a_group(
    db_session, monkeypatch,
):
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    await set_setting(
        db_session, "stats.exclusions", json.dumps([{"mode": "exact", "value": "Test Intro"}]),
    )
    play(db_session, utc(2026, 10, 14, 12))
    play(db_session, utc(2026, 9, 1, 12))
    play(db_session, utc(2026, 10, 14, 13), item="Test Intro")
    play(db_session, utc(2026, 10, 14, 14), library=None)
    await db_session.commit()

    chart = await get_daily_chart_data(db_session, days=30)

    assert chart["data"]["2026-10-14"]["Films"]["count"] == 1
    assert "2026-09-01" not in chart["data"]
    assert sum(len(groups) for groups in chart["data"].values()) == 1


@pytest.mark.asyncio
async def test_the_heatmap_follows_the_local_weekday_and_hour(db_session, monkeypatch):
    """Sunday 22:30 UTC is Monday 00:30 in Paris in October, and Sunday stays the first row."""
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    play(db_session, utc(2026, 10, 18, 22, 30))
    play(db_session, utc(2026, 10, 17, 12))
    await db_session.commit()

    in_utc = await get_weekly_heatmap(db_session, days=30)
    await save_paris(db_session)
    in_paris = await get_weekly_heatmap(db_session, days=30)

    assert in_utc["grid"][0][22] == 1
    assert in_utc["grid"][6][12] == 1
    assert in_paris["grid"][1][0] == 1
    assert in_paris["grid"][6][14] == 1
    assert sum(map(sum, in_paris["grid"])) == 2
    assert in_paris["days"][0] == "Dim"


@pytest.mark.asyncio
async def test_the_heatmap_counts_each_play_and_keeps_the_window(db_session, monkeypatch):
    freeze(monkeypatch, utc(2026, 10, 20, 12))
    await set_setting(
        db_session, "stats.exclusions", json.dumps([{"mode": "exact", "value": "Test Intro"}]),
    )
    monday_noon = utc(2026, 10, 12, 12)
    play(db_session, monday_noon)
    play(db_session, monday_noon)
    play(db_session, monday_noon, item="Test Intro")
    play(db_session, utc(2026, 8, 3, 12))
    await db_session.commit()

    heatmap = await get_weekly_heatmap(db_session, days=30)

    assert heatmap["grid"][1][12] == 2
    assert sum(map(sum, heatmap["grid"])) == 2
    assert heatmap["period_days"] == 30
