"""The watched hours of a playback's start wait until its player proves it plays."""
from datetime import UTC, date, datetime, timedelta
from itertools import cycle
from unittest.mock import AsyncMock, patch

import pytest

from services.portal.watch_days import watch_days
from services.stats_collector import _held_hours as held_hours
from services.stats_collector import _player_reports as reports
from services.stats_collector import _resume_zones as zones
from tests._watch_measurement_helpers import (
    STEP,
    T0,
    TICK,
    emby_session,
    known_application,
    poll,
    rows,
    saved,
)

pytestmark = pytest.mark.asyncio
FILM = 10800  # 3 h: Emby saves from 324 s
BEGIN = T0 + timedelta(hours=1)
HOUR = "2026-03-07T21"
# Steps of a real player between two polls 5 s apart.
REAL_STEPS = [3, 7, 4, 6, 3, 9, 3, 5, 4, 6, 4, 6, 4, 6, 4, 6, 3, 8, 3, 6, 5, 6, 3, 6]


@pytest.fixture(autouse=True)
def _reset_player_reports():
    reports._writers.clear()
    reports._last_stored.clear()
    yield
    reports._writers.clear()
    reports._last_stored.clear()


def _library_saves_from(min_pct: float, min_duration_s: int = 120) -> None:
    zones._zones["Films"] = zones.ResumeZone(min_pct, min_duration_s * TICK)


def _saved_by_emby(position_s: float, runtime_s: int = FILM, item: str = "MOVIE-1") -> dict:
    """What Emby keeps for a player reporting every 10 s: 0 before 3 % of the title."""
    reported = position_s - position_s % 10
    return saved(reported if reported >= runtime_s * 0.03 else 0, item=item)


async def _real(db, at, position, until, *, runtime_s=FILM, stored=_saved_by_emby, **kw):
    """A real player, one poll every 5 s. Returns (next poll, next position)."""
    while position <= until:
        session = emby_session(at=at, position_s=position, runtime_s=runtime_s, **kw)
        await poll(db, at, session, stored=stored(position, runtime_s))
        at, position = at + STEP, position + 5
    return at, position


async def _alone(db, at, position, until=400, *, runtime_s=FILM, stored=None, **kw):
    """The player is gone: Emby moves the session alone, nothing saved. Returns (next poll, next position)."""
    while position <= until:
        session = emby_session(at=at, position_s=position, runtime_s=runtime_s, **kw)
        await poll(db, at, session, stored=saved(0) if stored is None else stored)
        at, position = at + STEP, position + 5
    return at, position


async def _movie(db):
    (row,) = [r for r in await rows(db) if r.item_id == "MOVIE-1"]
    return row


def _hours(row) -> int:
    return sum((row.watched_by_hour or {}).values())


async def test_a_player_switched_off_at_the_start_of_a_long_film_fills_no_day(db_session):
    await known_application(db_session)
    _library_saves_from(3)
    at, position = await _real(db_session, BEGIN, 5, 5)
    at, _ = await _alone(db_session, at, position)  # past 324 s + 30 s: judged lost
    await poll(db_session, at)  # then Emby drops the session
    row = await _movie(db_session)
    # Only the first poll, judged before the row knew its library.
    assert row.watched_by_hour == {HOUR: 5}
    assert watch_days([row], UTC) == set()
    assert not held_hours._held


async def test_a_real_playback_keeps_each_second_in_the_hour_it_was_watched(db_session):
    await known_application(db_session)
    _library_saves_from(3)
    at, position = await _real(db_session, datetime(2026, 3, 7, 23, 59, 30, tzinfo=UTC), 5, 45, runtime_s=1440)
    assert (await _movie(db_session)).watched_by_hour == {"2026-03-07T23": 5}  # held until the save at 50 s
    at, _ = await _real(db_session, at, position, 1440, runtime_s=1440)
    await poll(db_session, at)
    row = await _movie(db_session)
    # Paid where each second was watched: those before midnight stay in the day before.
    assert row.watched_by_hour == {"2026-03-07T23": 30, "2026-03-08T00": 1410}
    assert row.exclusive_seconds == 1440


@pytest.mark.parametrize("paused", [False, True], ids=["stopped", "paused until the row closes"])
async def test_a_real_playback_ended_before_its_first_save_keeps_its_hours(db_session, paused):
    await known_application(db_session)
    _library_saves_from(3)
    at, position = await _real(db_session, BEGIN, 5, 120)
    assert _hours(await _movie(db_session)) == 5
    if paused:
        for minute in range(31):
            when = at + timedelta(minutes=minute)
            await poll(db_session, when, emby_session(at=when, position_s=position - 5, paused=True, runtime_s=FILM))
    else:
        await poll(db_session, at)
    row = await _movie(db_session)
    assert row.is_active is False
    assert row.watched_by_hour == {HOUR: 120}


async def test_a_seek_past_the_first_save_keeps_its_hours_once_the_player_saves(db_session):
    await known_application(db_session)
    _library_saves_from(3)
    for i, position in enumerate([5, 10, 15, 20, 25, 30, 1500, 1505, 1510]):
        at = BEGIN + STEP * i
        kept = 0 if position < 1505 else position - position % 10  # saved at the next report
        await poll(db_session, at, emby_session(at=at, position_s=position, runtime_s=2700), stored=saved(kept))
    row = await _movie(db_session)
    assert row.watched_by_hour == {HOUR: 45} and row.watched_seconds == 45


async def test_failed_reads_keep_a_player_judged_lost(db_session):
    await known_application(db_session)
    _library_saves_from(3)
    at, position = await _real(db_session, BEGIN, 5, 5)
    at, position = await _alone(db_session, at, position)
    at, _ = await _alone(db_session, at, position, 450, stored={})
    await poll(db_session, at)
    assert (await _movie(db_session)).watched_by_hour == {HOUR: 5}


async def test_a_position_saved_far_from_the_session_proves_nothing(db_session):
    # Another device of the account saves the film far from where Emby moves this session.
    await known_application(db_session)
    _library_saves_from(3)
    at, position = await _real(db_session, BEGIN, 5, 5)
    at, position = await _alone(db_session, at, position)
    at, _ = await _alone(db_session, at, position, 450, stored=saved(2000))
    await poll(db_session, at)
    assert (await _movie(db_session)).watched_by_hour == {HOUR: 5}


async def test_failed_reads_during_a_real_start_lose_no_hour(db_session):
    await known_application(db_session)
    _library_saves_from(3)

    def failing(position, runtime_s):
        return {} if 60 <= position < 120 else _saved_by_emby(position, runtime_s)

    await _real(db_session, BEGIN, 5, 400, stored=failing)
    row = await _movie(db_session)
    assert row.watched_by_hour == {HOUR: 400} and row.exclusive_seconds == 400


async def test_a_held_row_never_takes_the_time_of_another_device_of_the_account(db_session):
    # The TV dies 5 s into the film while the phone resumes an episode for 7 min.
    await known_application(db_session)
    _library_saves_from(3)
    at, tv, phone, steps = BEGIN, 5, 600, cycle(REAL_STEPS)
    while phone < 1020:
        episode = emby_session(at=at, position_s=phone, item="EP-1", item_type="Episode", runtime_s=2700,
                               session="S-2", device="PHONE", client="Android")
        stored = {**saved(0), **_saved_by_emby(phone, 2700, item="EP-1")}
        await poll(db_session, at, episode, emby_session(at=at, position_s=tv, runtime_s=FILM), stored=stored)
        at, tv, phone = at + STEP, tv + 5, phone + next(steps)
    at, _ = await _alone(db_session, at, tv, 500)
    await poll(db_session, at)
    film = await _movie(db_session)
    (episode,) = [r for r in await rows(db_session) if r.item_id == "EP-1"]
    assert episode.exclusive_seconds == episode.watched_seconds
    assert film.watched_by_hour == {HOUR: 5}
    assert watch_days([film, episode], UTC) == {date(2026, 3, 7)}


async def test_a_hold_judged_lost_only_for_want_of_a_read_is_paid(db_session):
    await known_application(db_session)
    _library_saves_from(3)
    for i in range(2):  # TV1 alone: held from its second poll
        at = BEGIN + STEP * i
        await poll(db_session, at, emby_session(at=at, position_s=5 + 5 * i, runtime_s=FILM), stored=saved(0))
    # TV2 plays the same film: Emby's saved position is no longer read. A 30 s gap after a minute.
    for i in [*range(2, 14), 20, 21]:
        at = BEGIN + STEP * i
        tv2 = emby_session(at=at, position_s=5 * (i - 1), runtime_s=FILM, session="S-2", device="DEVICE-2")
        await poll(db_session, at, emby_session(at=at, position_s=5 + 5 * i, runtime_s=FILM), tv2)
    await poll(db_session, at + STEP)
    (tv1,) = [r for r in await rows(db_session) if r.emby_session_key == "EMBY-1_MOVIE-1_S-1"]
    assert tv1.watched_by_hour == {HOUR: 10} and tv1.exclusive_seconds == 10
    assert not held_hours._held


@pytest.mark.parametrize("failing_at", [100, 330], ids=["while held", "when paid"])
async def test_a_failed_pass_neither_counts_held_hours_twice_nor_loses_them(db_session, failing_at):
    await known_application(db_session)
    _library_saves_from(3)
    at, position = BEGIN, 5
    while position <= 400:
        session = emby_session(at=at, position_s=position, runtime_s=FILM)
        if position == failing_at:  # the database refuses this pass, the next one measures it again
            failing = AsyncMock(side_effect=RuntimeError("database is locked"))
            with patch("services.stats_collector.collect.record_completions", new=failing), \
                 pytest.raises(RuntimeError):
                await poll(db_session, at, session, stored=_saved_by_emby(position))
            await db_session.rollback()
        else:
            await poll(db_session, at, session, stored=_saved_by_emby(position))
        at, position = at + STEP, position + 5
    row = await _movie(db_session)
    assert row.watched_by_hour == {HOUR: 400} and row.exclusive_seconds == 400


async def test_without_resume_settings_a_long_title_is_held_too(db_session):
    await known_application(db_session)
    at, position = await _real(db_session, BEGIN, 5, 5, runtime_s=3600)
    at, _ = await _alone(db_session, at, position, 420, runtime_s=3600)  # past 10 % of the title: judged lost
    await poll(db_session, at)
    assert (await _movie(db_session)).watched_by_hour == {HOUR: 5}


@pytest.mark.parametrize("learned, settings, runtime_s, device", [
    pytest.param(False, (3, 120), FILM, "DEVICE-1", id="application never seen saving"),
    pytest.param(True, (3, 120), FILM, "DEVICE-2", id="device never seen saving"),
    pytest.param(True, (3, FILM + 1), FILM, "DEVICE-1", id="title too short to be resumed"),
    pytest.param(True, None, 3000, "DEVICE-1", id="no settings, title under an hour"),
])
async def test_what_a_save_at_zero_cannot_judge_is_never_held(db_session, learned, settings, runtime_s, device):
    if learned:
        await known_application(db_session)
    if settings:
        _library_saves_from(*settings)
    at, position = await _real(db_session, BEGIN, 5, 5, runtime_s=runtime_s, device=device)
    at, _ = await _alone(db_session, at, position, runtime_s=runtime_s, device=device)
    await poll(db_session, at)
    row = await _movie(db_session)
    assert row.exclusive_seconds > 300 and row.watched_by_hour == {HOUR: row.exclusive_seconds}


async def test_the_first_poll_is_held_when_the_session_already_had_a_row(db_session):
    await known_application(db_session)
    _library_saves_from(3)
    at, _ = await _real(db_session, BEGIN, 5, 60)
    await poll(db_session, at)  # stopped before the first save: its minute counts
    at, position = await _real(db_session, at + timedelta(hours=1), 25, 25)  # same session, the TV dies at once
    at, _ = await _alone(db_session, at, position)
    await poll(db_session, at)
    first, second = [r for r in await rows(db_session) if r.item_id == "MOVIE-1"]
    assert first.watched_by_hour == {HOUR: 60}
    assert second.watched_by_hour is None and second.watched_seconds > 300


async def test_a_hold_is_forgotten_with_its_row(db_session):
    await known_application(db_session)
    _library_saves_from(3)
    at, _ = await _real(db_session, BEGIN, 5, 60)
    assert held_hours._held
    await db_session.delete(await _movie(db_session))  # erased at the viewer's request
    await db_session.commit()
    await poll(db_session, at)
    assert not held_hours._held
