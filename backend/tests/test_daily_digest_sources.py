"""The leaf sources of the daily digest: level progress, the month's ranking
rows and the library additions since the viewer last caught up."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from models.portal.profile import UserProfile
from models.user import User
from services.portal import daily_digest_sources as dd_sources
from services.portal.xp import MAX_LEVEL, xp_for_level


def test_level_info_below_max_progresses_to_next():
    """A mid-level profile reports progress toward the next level."""
    floor, ceiling = xp_for_level(5), xp_for_level(6)
    profile = UserProfile(level=5, xp=floor + (ceiling - floor) // 2)
    info = dd_sources.level_info(profile)
    assert info["maxed"] is False
    assert info["xp_next_level"] == ceiling
    assert 40 <= info["percent"] <= 60


def test_level_info_first_level_starts_at_0_xp():
    """Level 1 runs from 0 XP: at 50 XP the bar reads 50 / 300 and moves."""
    info = dd_sources.level_info(UserProfile(level=1, xp=50))
    assert info["xp_current_level"] == 0
    assert info["xp_next_level"] == 300
    assert info["xp_into_level"] == 50
    assert info["percent"] == 17


def test_level_info_at_max_level_is_full_and_capped():
    """At the cap the bar is full and there is no phantom level 51."""
    profile = UserProfile(level=MAX_LEVEL, xp=xp_for_level(MAX_LEVEL) + 1490)
    info = dd_sources.level_info(profile)
    assert info["maxed"] is True
    assert info["percent"] == 100
    assert info["xp_next_level"] == info["xp_current_level"] == xp_for_level(MAX_LEVEL)


@pytest.mark.asyncio
async def test_ranking_snapshot_keeps_the_level_of_each_row(db_session):
    """The digest writes each player's level, the viewer's fourth row included."""
    rows = [{"rank": rank, "level": 40 - rank, "is_current_user": False} for rank in (1, 2, 3)]
    rows.append({"rank": 8, "level": 12, "is_current_user": True})
    ranking = {"position": 8, "total": 8, "movement": 0, "leaderboard": rows}
    with patch.object(dd_sources, "compute_ranking", AsyncMock(return_value=ranking)):
        snapshot = await dd_sources.ranking_snapshot(db_session, User(username="alice"))
    assert [row["level"] for row in snapshot["top3"]] == [39, 38, 37, 12]


@pytest.mark.asyncio
async def test_ranking_snapshot_keeps_the_trophies_of_each_row(db_session):
    """The digest shows the trophies won, and a row without any stays at zero."""
    rows = [
        {"rank": 1, "trophies_won": 3, "is_current_user": False},
        {"rank": 2, "is_current_user": True},
    ]
    ranking = {"position": 2, "total": 2, "movement": 0, "leaderboard": rows}
    with patch.object(dd_sources, "compute_ranking", AsyncMock(return_value=ranking)):
        snapshot = await dd_sources.ranking_snapshot(db_session, User(username="alice"))
    assert [row["trophies_won"] for row in snapshot["top3"]] == [3, 0]


def _fake_adds(count: int) -> list[dict]:
    """``count`` items dated day-0..day-(count-1), newest first (Emby DESC)."""
    today = datetime.now(UTC).date()
    return [
        {
            "tmdb_id": i, "emby_item_id": str(i), "title": f"T{i}", "year": "2024",
            "media_type": "movie", "poster_url": "",
            "date_created": (today - timedelta(days=i)).isoformat(),
        }
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_recent_adds_keeps_only_items_after_since(db_session):
    """Items strictly newer than the since-date are kept, older ones dropped."""
    since = datetime.now(UTC) - timedelta(days=10)
    with patch.object(dd_sources, "get_recently_added", AsyncMock(return_value=_fake_adds(40))):
        out = await dd_sources.recent_adds(db_session, since=since)
    # since.date() == today-10; strict ">" keeps days 0..9 only.
    assert [it["tmdb_id"] for it in out] == list(range(10))
    assert all("backdrop_url" not in it for it in out)  # dead field dropped


@pytest.mark.asyncio
async def test_recent_adds_caps_at_30(db_session):
    """A long catch-up window is capped at 30 posters, newest first."""
    since = datetime.now(UTC) - timedelta(days=100)
    with patch.object(dd_sources, "get_recently_added", AsyncMock(return_value=_fake_adds(40))):
        out = await dd_sources.recent_adds(db_session, since=since)
    assert [it["tmdb_id"] for it in out] == list(range(30))


@pytest.mark.asyncio
async def test_recent_adds_keeps_same_day_item_added_after_watermark(db_session):
    """An item added later on the SAME calendar day as the watermark is kept —
    the full-timestamp comparison fixes the day-granular drop."""
    now = datetime.now(UTC)
    since = now - timedelta(hours=3)  # watermark earlier today
    day = now.date().isoformat()
    items = [
        {  # added after the watermark, same day -> kept
            "tmdb_id": 1, "emby_item_id": "1", "title": "After", "year": "2024",
            "media_type": "movie", "poster_url": "", "date_created": day,
            "date_created_at": (now - timedelta(hours=1)).isoformat(),
        },
        {  # added before the watermark, same day -> dropped
            "tmdb_id": 2, "emby_item_id": "2", "title": "Before", "year": "2024",
            "media_type": "movie", "poster_url": "", "date_created": day,
            "date_created_at": (now - timedelta(hours=5)).isoformat(),
        },
    ]
    with patch.object(dd_sources, "get_recently_added", AsyncMock(return_value=items)):
        out = await dd_sources.recent_adds(db_session, since=since)
    assert [it["tmdb_id"] for it in out] == [1]
