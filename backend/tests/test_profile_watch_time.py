"""Profile watch time counts what was watched, not how long sessions stayed open."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from models.playback_stats import PlaybackSession
from services.portal.profile_stats_playback import compute_totals

_TICKS_PER_MINUTE = 60 * 10_000_000
_START = datetime(2026, 1, 5, 20, 0, tzinfo=timezone.utc)
_USER = PlaybackSession.user_id == "u-watch"


def _session(key: str, *, wall: timedelta, position_min: int, runtime_min: int) -> PlaybackSession:
    return PlaybackSession(
        session_key=key,
        user_id="u-watch",
        user_name="viewer",
        item_id=f"item-{key}",
        item_name="Sample title",
        item_type="Movie",
        started_at=_START,
        last_seen_at=_START + wall,
        ended_at=_START + wall,
        is_active=False,
        position_ticks=position_min * _TICKS_PER_MINUTE,
        duration_ticks=runtime_min * _TICKS_PER_MINUTE,
    )


async def _totals(db_session, *rows: PlaybackSession) -> tuple[int, int]:
    db_session.add_all(rows)
    await db_session.commit()
    return await compute_totals(db_session, _USER, [])


@pytest.mark.asyncio
async def test_session_spread_over_days_counts_the_reached_position(db_session):
    row = _session("a", wall=timedelta(days=3), position_min=30, runtime_min=120)
    assert await _totals(db_session, row) == (1, 30)


@pytest.mark.asyncio
async def test_overnight_pause_is_not_counted(db_session):
    row = _session("a", wall=timedelta(hours=9), position_min=60, runtime_min=120)
    assert (await _totals(db_session, row))[1] == 60


@pytest.mark.asyncio
async def test_runtime_caps_a_session_without_position(db_session):
    row = _session("a", wall=timedelta(hours=3), position_min=0, runtime_min=60)
    assert (await _totals(db_session, row))[1] == 60


@pytest.mark.asyncio
async def test_wall_clock_counts_when_it_is_the_smallest(db_session):
    # Resumed mid-film: the reached position overstates the 40 minutes watched.
    row = _session("a", wall=timedelta(minutes=40), position_min=100, runtime_min=120)
    assert (await _totals(db_session, row))[1] == 40


@pytest.mark.asyncio
async def test_sessions_add_up_and_no_session_means_zero(db_session):
    assert await compute_totals(db_session, _USER, []) == (0, 0)
    rows = (
        _session("a", wall=timedelta(hours=2), position_min=50, runtime_min=50),
        _session("b", wall=timedelta(days=1), position_min=45, runtime_min=45),
    )
    assert await _totals(db_session, *rows) == (2, 95)
