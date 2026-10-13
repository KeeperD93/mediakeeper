"""Profile watch time counts what was watched, not how long sessions stayed open."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from models.playback_stats import PlaybackSession
from services.portal.achievements_utils import _session_duration_seconds
from services.portal.profile_stats_playback import compute_totals
from services.portal.profile_stats_viewing import compute_media_type_ratio

_TICKS_PER_MINUTE = 60 * 10_000_000
_START = datetime(2026, 1, 5, 20, 0, tzinfo=timezone.utc)
_USER = PlaybackSession.user_id == "u-watch"


def _session(
    key: str, *, wall: timedelta, position_min: int, runtime_min: int, item_type: str = "Movie",
    watched_min: int | None = None, counted_min: int | None = None,
) -> PlaybackSession:
    """A session; ``watched_min`` / ``counted_min`` set the measured time (``None`` = not measured)."""
    row = PlaybackSession(
        session_key=key,
        user_id="u-watch",
        user_name="viewer",
        item_id=f"item-{key}",
        item_name="Sample title",
        item_type=item_type,
        started_at=_START,
        last_seen_at=_START + wall,
        ended_at=_START + wall,
        is_active=False,
        position_ticks=position_min * _TICKS_PER_MINUTE,
        duration_ticks=runtime_min * _TICKS_PER_MINUTE,
    )
    if watched_min is not None:
        row.watched_seconds = watched_min * 60
        row.exclusive_seconds = (watched_min if counted_min is None else counted_min) * 60
        row.measured = True
    return row


async def _store(db_session, *rows: PlaybackSession) -> None:
    db_session.add_all(rows)
    await db_session.commit()


@pytest.mark.asyncio
async def test_profile_total_is_the_measured_watch_time(db_session):
    # A night-long pause around 40 measured minutes adds nothing.
    await _store(db_session, _session("a", wall=timedelta(hours=9), position_min=60, runtime_min=120, watched_min=40))
    assert await compute_totals(db_session, _USER, []) == (1, 40)


@pytest.mark.asyncio
async def test_sessions_add_up_and_no_session_means_zero(db_session):
    assert await compute_totals(db_session, _USER, []) == (0, 0)
    await _store(
        db_session,
        _session("a", wall=timedelta(hours=2), position_min=50, runtime_min=50, watched_min=50),
        _session("b", wall=timedelta(days=1), position_min=45, runtime_min=45, watched_min=45),
    )
    assert await compute_totals(db_session, _USER, []) == (2, 95)


@pytest.mark.asyncio
async def test_music_and_concurrent_plays_are_not_counted_twice(db_session):
    await _store(
        db_session,
        _session("song", wall=timedelta(hours=1), position_min=60, runtime_min=60,
                 item_type="Audio", watched_min=60, counted_min=0),
        _session("second-device", wall=timedelta(hours=1), position_min=30, runtime_min=60,
                 watched_min=30, counted_min=0),
    )
    assert (await compute_totals(db_session, _USER, []))[1] == 0


@pytest.mark.asyncio
async def test_movie_series_split_uses_the_measured_time(db_session):
    await _store(
        db_session,
        _session("a", wall=timedelta(days=3), position_min=30, runtime_min=120, watched_min=30),
        _session("b", wall=timedelta(minutes=45), position_min=45, runtime_min=45,
                 item_type="Episode", watched_min=45),
    )
    assert await compute_media_type_ratio(db_session, _USER, []) == {
        "movie_plays": 1, "movie_minutes": 30, "series_plays": 1, "series_minutes": 45,
    }


@pytest.mark.parametrize(
    ("wall", "position_min", "runtime_min", "expected_min"),
    [
        (timedelta(days=3), 30, 120, 30),         # session open for days: the position bounds it
        (timedelta(hours=3), 0, 60, 60),          # no position reported: the runtime bounds it
        (timedelta(minutes=40), 100, 120, 40),    # resumed mid-title: the wall clock is smallest
    ],
)
def test_unmeasured_sessions_fall_back_to_the_estimate(wall, position_min, runtime_min, expected_min):
    row = _session("a", wall=wall, position_min=position_min, runtime_min=runtime_min)
    assert _session_duration_seconds(row) == expected_min * 60


def test_unmeasured_music_never_counts():
    row = _session("a", wall=timedelta(hours=1), position_min=60, runtime_min=60, item_type="Audio")
    assert _session_duration_seconds(row) == 0
