"""A player gone while Emby keeps moving its session: what counts, and when the row ends."""
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from services.stats_collector import _player_reports as reports
from services.stats_collector._measure import as_utc
from tests._watch_measurement_helpers import (
    STEP,
    T0,
    TICK,
    completions,
    poll,
    rows,
    saved,
    session,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_player_reports():
    reports._writers.clear()
    reports._last_stored.clear()
    yield
    reports._writers.clear()
    reports._last_stored.clear()


async def _play_reporting(db, first_position: float, count: int, **kw):
    """``count`` polls of a player reporting every 10 s. Returns (last poll, position, saved position)."""
    item = kw.get("item", "MOVIE-1")
    for i in range(count):
        at, position, position_saved = T0 + STEP * i, first_position + 5 * i, first_position + 10 * (i // 2)
        await poll(db, at, session(at=at, position_s=position, **kw), stored=saved(position_saved, item=item))
    return at, position, position_saved


async def _emby_alone(db, last, position: float, position_saved: float, count: int, **kw):
    """The player is gone: Emby moves the position alone, the saved position stays. Returns (last poll, position)."""
    for i in range(1, count + 1):
        at, moved = last + STEP * i, position + 4.5 * i
        await poll(db, at, session(at=at, position_s=moved, **kw), stored=saved(position_saved))
    return at, moved


async def test_a_lost_player_stops_counting(db_session):
    last, position, position_saved = await _play_reporting(db_session, 2000, 25)
    await _emby_alone(db_session, last, position, position_saved, 40)
    (row,) = await rows(db_session)
    # 120 s played, then only what passes before the session is 30 s from the saved position.
    assert row.watched_seconds == 147
    assert row.position_ticks < (position + 35) * TICK
    assert as_utc(row.last_seen_at) < last + timedelta(seconds=40)


async def test_what_the_buffer_played_counts_when_the_player_is_back(db_session):
    last, position, position_saved = await _play_reporting(db_session, 2000, 25)
    held, _ = await _emby_alone(db_session, last, position, position_saved, 30)
    back = held + STEP
    await poll(db_session, back, session(at=back, position_s=position + 60), stored=saved(position + 58))
    (row,) = await rows(db_session)
    assert row.watched_seconds == 120 + 60


async def test_an_application_that_never_saves_keeps_the_activity_rule(db_session):
    # Saved position frozen where the viewing started: nothing proves this application reports it.
    for i in range(120):
        at = T0 + STEP * i
        await poll(db_session, at, session(at=at, position_s=2880 + 5 * i), stored=saved(2880))
    (row,) = await rows(db_session)
    assert row.watched_seconds == 595
    assert not reports._writers


async def test_a_saved_position_that_stays_out_of_reach_proves_nothing(db_session):
    # Known application, new title, saved position left far away by an earlier viewing.
    await _play_reporting(db_session, 1000, 4, item="OTHER", session="S-0")
    for i in range(60):
        at = T0 + timedelta(hours=1) + STEP * i
        await poll(db_session, at, session(at=at, position_s=2000 + 5 * i), stored=saved(5000))
    new = (await rows(db_session))[-1]
    assert new.watched_seconds == 295


async def test_a_failed_read_does_not_release_a_held_row(db_session):
    last, position, position_saved = await _play_reporting(db_session, 2000, 25)
    held, moved = await _emby_alone(db_session, last, position, position_saved, 30)
    failed = held + STEP
    await poll(db_session, failed, session(at=failed, position_s=moved + 4.5))
    await _emby_alone(db_session, failed, moved + 4.5, position_saved, 10)
    (row,) = await rows(db_session)
    assert row.watched_seconds == 147


async def test_a_failed_read_during_normal_playback_loses_nothing(db_session):
    last, position, _ = await _play_reporting(db_session, 2000, 25)
    at = last + STEP
    await poll(db_session, at, session(at=at, position_s=position + 5))
    (row,) = await rows(db_session)
    assert row.watched_seconds == 125


async def test_saved_at_zero_far_into_a_film_means_the_player_is_lost(db_session):
    await _play_reporting(db_session, 1000, 4, item="OTHER", session="S-0")
    start = T0 + timedelta(hours=1)
    for i in range(8):
        at = start + STEP * i
        await poll(db_session, at, session(at=at, position_s=700 + 5 * i, runtime_s=7200), stored=saved(0))
    (row,) = [r for r in await rows(db_session) if r.item_id == "MOVIE-1"]
    # 10 % of the film is 720 s: nothing counts from there.
    assert row.watched_seconds == 15


@pytest.mark.parametrize("runtime, played, expected", [
    (1800, False, 35),  # a short title may never get a resume position
    (7200, True, 35),   # at 0 and marked played: past the end of the resume zone
])
async def test_saved_at_zero_proves_nothing_elsewhere(db_session, runtime, played, expected):
    await _play_reporting(db_session, 1000, 4, item="OTHER", session="S-0")
    start = T0 + timedelta(hours=1)
    for i in range(8):
        at = start + STEP * i
        await poll(db_session, at, session(at=at, position_s=700 + 5 * i, runtime_s=runtime), stored=saved(0, played=played))
    (row,) = [r for r in await rows(db_session) if r.item_id == "MOVIE-1"]
    assert row.watched_seconds == expected


async def test_an_application_is_known_per_library(db_session):
    await _play_reporting(db_session, 1000, 4, client="Theater")
    assert reports._writers == {("Theater", "Films")}


async def test_a_row_ends_at_its_last_real_second_after_thirty_minutes(db_session):
    last, position, position_saved = await _play_reporting(db_session, 2000, 25)
    grant = AsyncMock()
    for minute in range(1, 40):
        at = last + timedelta(minutes=minute)
        await poll(db_session, at, session(at=at, position_s=position + 54 * minute), stored=saved(position_saved), grant=grant)
    (row,) = await rows(db_session)
    assert row.is_active is False and as_utc(row.ended_at) == last
    assert row.watched_seconds == 120
    grant.assert_awaited_once()
    # Back the next day: a new row, with only what is really played.
    back = last + timedelta(days=1)
    await poll(db_session, back, session(at=back, position_s=5000), stored=saved(4998))
    first, second = await rows(db_session)
    assert second.is_active is True and second.watched_seconds == 0 and first.is_active is False


async def test_a_return_within_thirty_minutes_stays_on_the_row(db_session):
    last, position, position_saved = await _play_reporting(db_session, 2000, 25)
    for minute in range(1, 25):
        at = last + timedelta(minutes=minute)
        await poll(db_session, at, session(at=at, position_s=position + 54 * minute), stored=saved(position_saved))
    back = last + timedelta(minutes=25)
    await poll(db_session, back, session(at=back, position_s=position + 200), stored=saved(position + 198))
    (row,) = await rows(db_session)
    assert row.is_active is True and row.watched_seconds == 320


async def test_a_lost_activity_jump_neither_extends_nor_reopens_the_row(db_session):
    last, position, _ = await _play_reporting(db_session, 2000, 25)
    jump = last + timedelta(minutes=10)
    await poll(db_session, jump, session(at=jump, position_s=position), stored=saved(position))
    (row,) = await rows(db_session)
    assert as_utc(row.last_seen_at) == last
    # The session stays listed, frozen: the row ends, a later jump opens nothing.
    closing = last + timedelta(minutes=31)
    await poll(db_session, closing, session(at=closing, position_s=position, silent_since=jump), stored=saved(position))
    second_jump = last + timedelta(hours=2)
    await poll(db_session, second_jump, session(at=second_jump, position_s=position), stored=saved(position))
    (row,) = await rows(db_session)
    assert row.is_active is False and as_utc(row.ended_at) == last


async def test_a_collector_outage_keeps_one_row_and_all_its_time(db_session):
    last, position, _ = await _play_reporting(db_session, 2000, 25)
    back = last + timedelta(minutes=35)
    await poll(db_session, back, session(at=back, position_s=position + 2100), stored=saved(position + 2098))
    (row,) = await rows(db_session)
    assert row.is_active is True and row.watched_seconds == 120 + 2100


async def test_a_pause_longer_than_the_limit_makes_two_rows(db_session):
    last, position, position_saved = await _play_reporting(db_session, 2000, 25)
    for minute in range(1, 41):
        at = last + timedelta(minutes=minute)
        await poll(db_session, at, session(at=at, position_s=position, paused=True), stored=saved(position_saved))
    start = last + timedelta(minutes=41)
    for i in range(13):
        at = start + STEP * i
        await poll(db_session, at, session(at=at, position_s=position + 1 + 5 * i), stored=saved(position + 1 + 10 * (i // 2)))
    first, second = await rows(db_session)
    assert first.is_active is False and as_utc(first.ended_at) == last
    assert first.watched_seconds == 120 and second.watched_seconds == 60


async def test_a_return_from_a_made_up_position_is_capped(db_session):
    last, position, position_saved = await _play_reporting(db_session, 2000, 25)
    held, moved = await _emby_alone(db_session, last, position, position_saved, 30)
    gone = held + timedelta(minutes=1)
    await poll(db_session, gone)   # Emby stops the playback and saves the position it made up
    fake = moved + 1000
    back = gone + timedelta(minutes=15)
    await poll(db_session, back, session(at=back, position_s=fake), stored=saved(fake))
    (row,) = await rows(db_session)
    assert row.is_active is True and row.watched_seconds == 147 + 300


async def test_a_session_without_position_keeps_its_wall_time(db_session):
    for minute in range(41):
        at = T0 + timedelta(minutes=minute)
        await poll(db_session, at, session(at=at, position_s=0, item_type="TvChannel"))
    (row,) = await rows(db_session)
    assert row.is_active is True and as_utc(row.last_seen_at) == T0 + timedelta(minutes=40)


async def test_a_restart_from_the_beginning_is_not_a_leftover(db_session):
    last, position, _ = await _play_reporting(db_session, 2000, 25)
    await poll(db_session, last + STEP)  # stopped
    again = last + timedelta(hours=3)
    await poll(db_session, again, session(at=again, position_s=8), stored=saved(position))
    first, second = await rows(db_session)
    assert second.is_active is True and second.watched_seconds == 8
    assert first.is_active is False


async def test_a_title_marked_watched_needs_real_viewing(db_session):
    last, position, position_saved = await _play_reporting(db_session, 200, 25, runtime_s=600)
    for i in range(1, 80):
        at = last + STEP * i
        await poll(db_session, at, session(at=at, position_s=position + 4.5 * i, runtime_s=600), stored=saved(position_saved))
    assert await completions(db_session) == []


async def test_saved_positions_are_forgotten_with_their_session(db_session):
    last, *_ = await _play_reporting(db_session, 2000, 3)
    assert reports._last_stored
    await poll(db_session, last + STEP)
    assert not reports._last_stored
