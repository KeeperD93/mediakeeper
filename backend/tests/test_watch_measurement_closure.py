"""When a row ends, and what may open or reopen one."""
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from services.stats_collector import _player_reports as reports
from services.stats_collector._measure import as_utc
from tests._watch_measurement_helpers import (
    STEP,
    T0,
    TICK,
    emby_alone,
    emby_session,
    play_reporting,
    poll,
    rows,
    saved,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_player_reports():
    reports._writers.clear()
    reports._last_stored.clear()
    yield
    reports._writers.clear()
    reports._last_stored.clear()


async def test_a_row_ends_at_its_last_real_second_after_thirty_minutes(db_session):
    last, position, position_saved = await play_reporting(db_session, 2000, 25)
    grant = AsyncMock()
    for minute in range(1, 40):
        at = last + timedelta(minutes=minute)
        await poll(db_session, at, emby_session(at=at, position_s=position + 54 * minute), stored=saved(position_saved), grant=grant)
    (row,) = await rows(db_session)
    assert row.is_active is False and as_utc(row.ended_at) == last
    assert row.watched_seconds == 120
    grant.assert_awaited_once()
    # Back the next day: a new row, with only what is really played.
    back = last + timedelta(days=1)
    await poll(db_session, back, emby_session(at=back, position_s=5000), stored=saved(4998))
    first, second = await rows(db_session)
    assert second.is_active is True and second.watched_seconds == 0 and first.is_active is False


async def test_a_return_within_thirty_minutes_stays_on_the_row(db_session):
    last, position, position_saved = await play_reporting(db_session, 2000, 25)
    for minute in range(1, 25):
        at = last + timedelta(minutes=minute)
        await poll(db_session, at, emby_session(at=at, position_s=position + 54 * minute), stored=saved(position_saved))
    back = last + timedelta(minutes=25)
    await poll(db_session, back, emby_session(at=back, position_s=position + 200), stored=saved(position + 198))
    (row,) = await rows(db_session)
    assert row.is_active is True and row.watched_seconds == 320


async def test_a_lost_activity_jump_neither_extends_nor_reopens_the_row(db_session):
    last, position, _ = await play_reporting(db_session, 2000, 25)
    jump = last + timedelta(minutes=10)
    await poll(db_session, jump, emby_session(at=jump, position_s=position), stored=saved(position))
    (row,) = await rows(db_session)
    assert as_utc(row.last_seen_at) == last
    # The session stays listed, frozen: the row ends, a later jump opens nothing.
    closing = last + timedelta(minutes=31)
    await poll(db_session, closing, emby_session(at=closing, position_s=position, silent_since=jump), stored=saved(position))
    second_jump = last + timedelta(hours=2)
    await poll(db_session, second_jump, emby_session(at=second_jump, position_s=position), stored=saved(position))
    (row,) = await rows(db_session)
    assert row.is_active is False and as_utc(row.ended_at) == last


async def _closed_by_silence(db):
    """A known application lost, its row closed, Emby still moving the session. Returns (last poll, position)."""
    last, position, position_saved = await play_reporting(db, 2000, 25)
    for minute in range(1, 32):
        at = last + timedelta(minutes=minute)
        moved = position + 60 * minute
        await poll(db, at, emby_session(at=at, position_s=moved), stored=saved(position_saved))
    return at, moved


async def test_a_failed_read_does_not_open_a_row_for_a_leftover(db_session):
    at, moved = await _closed_by_silence(db_session)
    failed = at + timedelta(minutes=1)
    await poll(db_session, failed, emby_session(at=failed, position_s=moved + 60))
    assert len(await rows(db_session)) == 1


async def test_a_saved_position_moved_by_another_device_does_not_open_a_row_for_a_leftover(db_session):
    at, moved = await _closed_by_silence(db_session)
    later = at + timedelta(minutes=1)
    await poll(db_session, later, emby_session(at=later, position_s=moved + 60), stored=saved(100))
    assert len(await rows(db_session)) == 1


async def test_the_latest_closed_row_is_the_one_resumed(db_session):
    await poll(db_session, T0, emby_session(at=T0, position_s=100))
    await poll(db_session, T0 + STEP)  # first sitting over
    evening = T0 + timedelta(hours=20)
    await poll(db_session, evening, emby_session(at=evening, position_s=500))
    await poll(db_session, evening + STEP)  # second sitting, dropped by Emby
    back = evening + timedelta(minutes=2)
    await poll(db_session, back, emby_session(at=back, position_s=510))
    first, second = await rows(db_session)
    assert first.is_active is False and second.is_active is True


async def test_going_back_is_remembered_even_when_it_earns_nothing(db_session):
    await poll(db_session, T0, emby_session(at=T0, position_s=600))
    at = T0 + STEP
    await poll(db_session, at, emby_session(at=at, position_s=300))
    (row,) = await rows(db_session)
    assert row.position_ticks == 300 * TICK and row.watched_seconds == 0


async def test_a_collector_outage_keeps_one_row_and_all_its_time(db_session):
    last, position, _ = await play_reporting(db_session, 2000, 25)
    back = last + timedelta(minutes=35)
    await poll(db_session, back, emby_session(at=back, position_s=position + 2100), stored=saved(position + 2098))
    (row,) = await rows(db_session)
    assert row.is_active is True and row.watched_seconds == 120 + 2100


async def test_a_pause_longer_than_the_limit_makes_two_rows(db_session):
    last, position, position_saved = await play_reporting(db_session, 2000, 25)
    for minute in range(1, 41):
        at = last + timedelta(minutes=minute)
        await poll(db_session, at, emby_session(at=at, position_s=position, paused=True), stored=saved(position_saved))
    start = last + timedelta(minutes=41)
    for i in range(13):
        at = start + STEP * i
        await poll(db_session, at, emby_session(at=at, position_s=position + 1 + 5 * i), stored=saved(position + 1 + 10 * (i // 2)))
    first, second = await rows(db_session)
    assert first.is_active is False and as_utc(first.ended_at) == last
    assert first.watched_seconds == 120 and second.watched_seconds == 60


async def test_a_return_from_a_made_up_position_is_capped(db_session):
    last, position, position_saved = await play_reporting(db_session, 2000, 25)
    held, moved = await emby_alone(db_session, last, position, position_saved, 30)
    gone = held + timedelta(minutes=1)
    await poll(db_session, gone)   # Emby stops the playback and saves the position it made up
    fake = moved + 1000
    back = gone + timedelta(minutes=15)
    await poll(db_session, back, emby_session(at=back, position_s=fake), stored=saved(fake))
    (row,) = await rows(db_session)
    assert row.is_active is True and row.watched_seconds == 147 + 300


async def test_a_session_without_position_keeps_its_wall_time(db_session):
    for minute in range(41):
        at = T0 + timedelta(minutes=minute)
        await poll(db_session, at, emby_session(at=at, position_s=0, item_type="TvChannel"))
    (row,) = await rows(db_session)
    assert row.is_active is True and as_utc(row.last_seen_at) == T0 + timedelta(minutes=40)


async def test_a_second_sitting_without_position_gets_its_row(db_session):
    await poll(db_session, T0, emby_session(at=T0, position_s=0, item_type="TvChannel"))
    await poll(db_session, T0 + STEP)  # stopped
    later = T0 + timedelta(hours=1)
    await poll(db_session, later, emby_session(at=later, position_s=0, item_type="TvChannel"))
    first, second = await rows(db_session)
    assert first.is_active is False and second.is_active is True


async def test_a_restart_from_the_beginning_is_not_a_leftover(db_session):
    last, position, _ = await play_reporting(db_session, 2000, 25)
    await poll(db_session, last + STEP)  # stopped
    again = last + timedelta(hours=3)
    await poll(db_session, again, emby_session(at=again, position_s=8), stored=saved(position))
    first, second = await rows(db_session)
    assert second.is_active is True and second.watched_seconds == 8
    assert first.is_active is False
