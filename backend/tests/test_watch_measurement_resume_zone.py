"""A saved position still at 0 where Emby would already have saved one: the player is gone."""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.stats_collector import _player_reports as reports
from services.stats_collector import _resume_zones as zones
from services.stats_collector._player_reports import StoredPosition
from tests._watch_measurement_helpers import (
    STEP,
    T0,
    TICK,
    completions,
    emby_session,
    known_application,
    poll,
    rows,
    saved,
)

pytestmark = pytest.mark.asyncio
MIN = timedelta(minutes=1)


@pytest.fixture(autouse=True)
def _reset_player_reports():
    reports._writers.clear()
    reports._last_stored.clear()
    yield
    reports._writers.clear()
    reports._last_stored.clear()


def _library_saves_from(min_pct: float, min_duration_s: int = 120) -> None:
    zones._zones["Films"] = zones.ResumeZone(min_pct, min_duration_s * TICK)


def _saved_by_emby(position_s: float, runtime_s: int) -> dict:
    """What Emby keeps for a player reporting every 10 s: 0 before 3 %, a title played past 90 %."""
    reported = position_s - position_s % 10
    if reported < runtime_s * 0.03:
        return saved(0)
    if reported > runtime_s * 0.90:
        return saved(0, played=True)
    return saved(reported)


async def _movie_rows(db):
    return [r for r in await rows(db) if r.item_id == "MOVIE-1"]


@pytest.mark.parametrize("runtime, cut, start", [(7200, 150, 216), (2700, 60, 81), (1440, 30, 43.2)])
async def test_a_player_lost_before_its_first_save_stops_counting_past_it(db_session, runtime, cut, start):
    await known_application(db_session)
    _library_saves_from(3)
    begin = T0 + timedelta(hours=1)
    at, position = begin, 5.0
    while position <= cut:
        await poll(db_session, at, emby_session(at=at, position_s=position, runtime_s=runtime), stored=saved(0))
        at, position = at + STEP, position + 5
    for _ in range(12):  # the player is gone, Emby moves the session alone
        await poll(db_session, at, emby_session(at=at, position_s=position, runtime_s=runtime), stored=saved(0))
        at, position = at + STEP, position + 4.5
    while position < runtime - 60:  # then for as long as the title lasts, past the 30 min of silence
        await poll(db_session, at, emby_session(at=at, position_s=position, runtime_s=runtime), stored=saved(0))
        at, position = at + MIN, position + 60
    await poll(db_session, at)
    (row,) = await _movie_rows(db_session)
    # Nothing tells a cut before 3 %: counted up to one report past it, never more.
    assert cut <= row.watched_seconds <= start + 30
    assert not [c for c in await completions(db_session) if c.item_id == "MOVIE-1"]


async def test_a_device_never_seen_saving_keeps_the_previous_rule(db_session):
    # The application is known from another device; this one, an external player, saves nothing.
    await known_application(db_session)
    _library_saves_from(3)
    runtime, at, position = 1440, T0 + timedelta(hours=1), 5
    while position <= runtime:
        session = emby_session(at=at, position_s=position, runtime_s=runtime, session="S-2", device="DEVICE-2")
        await poll(db_session, at, session, stored=saved(0))
        at, position = at + STEP, position + 5
    await poll(db_session, at)
    (row,) = await _movie_rows(db_session)
    assert row.watched_seconds == runtime


async def test_a_setting_raised_in_emby_releases_a_held_row_in_time(db_session):
    # Read at 3 %, raised to 50 % five minutes in: the real player saves nothing before 50 %.
    settings = {"MinResumePct": 3, "MinResumeDurationSeconds": 120}

    async def read_settings(url, api_key, now):
        client = MagicMock()
        answer = [{"Name": "Films", "LibraryOptions": dict(settings)}]
        client.get = AsyncMock(return_value=httpx.Response(200, json=answer, request=httpx.Request("GET", url)))
        with patch("services.stats_collector._resume_zones.get_internal_client", return_value=client):
            await zones.refresh_resume_zones(url, api_key, now)

    await known_application(db_session)
    begin, step = T0 + timedelta(hours=1), timedelta(seconds=10)
    at, position = begin, 5
    while position <= 2400:  # 40 min of real playback
        if at - begin >= 5 * MIN:
            settings["MinResumePct"] = 50
        await poll(db_session, at, emby_session(at=at, position_s=position, runtime_s=7200), stored=saved(0),
                   refresh=AsyncMock(side_effect=read_settings))
        at, position = at + step, position + 10
    (row,) = await _movie_rows(db_session)
    assert row.watched_seconds == position - 10


async def test_a_real_playback_from_start_to_end_counts_every_second(db_session):
    await known_application(db_session)
    _library_saves_from(3)
    runtime, begin = 1440, T0 + timedelta(hours=1)
    at, position = begin, 5
    while position <= runtime:
        await poll(db_session, at, emby_session(at=at, position_s=position, runtime_s=runtime),
                   stored=_saved_by_emby(position, runtime))
        if position == 600:
            for _ in range(12):  # one minute paused
                at += STEP
                await poll(db_session, at, emby_session(at=at, position_s=position, paused=True, runtime_s=runtime))
        at, position = at + STEP, position + 5
    await poll(db_session, at)
    (row,) = await _movie_rows(db_session)
    assert row.watched_seconds == runtime
    assert [c.item_id for c in await completions(db_session)] == ["MOVIE-1"]


async def test_a_seek_past_the_first_save_counts_once_the_player_saves(db_session):
    await known_application(db_session)
    _library_saves_from(3)
    begin = T0 + timedelta(hours=1)
    positions = [5, 10, 15, 20, 25, 30, 1500, 1505, 1510, 1515, 1520]
    for i, position in enumerate(positions):
        at = begin + STEP * i
        # The seek is saved at the next report, one poll later.
        kept = 0 if position < 1505 else position - position % 10
        await poll(db_session, at, emby_session(at=at, position_s=position, runtime_s=2700), stored=saved(kept))
    (row,) = await _movie_rows(db_session)
    assert row.watched_seconds == 5 * len(positions)


@pytest.mark.parametrize("min_pct, min_duration_s, expected", [
    pytest.param(None, None, 15, id="settings unknown: 0 far into a long title"),
    pytest.param(3, 120, 15, id="started past the first save"),
    pytest.param(20, 120, 35, id="Emby only saves from 20 %"),
    pytest.param(3, 9000, 35, id="title too short to be resumed"),
])
async def test_a_save_at_zero_is_judged_on_the_library_settings(db_session, min_pct, min_duration_s, expected):
    await known_application(db_session)
    if min_pct is not None:
        _library_saves_from(min_pct, min_duration_s)
    start = T0 + timedelta(hours=1)
    for i in range(8):
        at = start + STEP * i
        await poll(db_session, at, emby_session(at=at, position_s=700 + 5 * i, runtime_s=7200), stored=saved(0))
    (row,) = await _movie_rows(db_session)
    assert row.watched_seconds == expected


async def test_a_new_playback_on_the_same_session_is_not_held_by_an_old_row(db_session):
    await known_application(db_session)
    _library_saves_from(3)
    first = T0 + timedelta(hours=1)
    for i in range(4):  # 20 s at the start, then the viewer stops
        at = first + STEP * i
        await poll(db_session, at, emby_session(at=at, position_s=5 + 5 * i, runtime_s=2700), stored=saved(0))
    await poll(db_session, first + STEP * 4)
    again = first + timedelta(minutes=40)
    for i in range(8):  # back on the same Emby session, the opening skipped up to 150 s
        at, position = again + STEP * i, 150 + 5 * i
        kept = 0 if i == 0 else position - position % 10
        await poll(db_session, at, emby_session(at=at, position_s=position, runtime_s=2700), stored=saved(kept))
    assert [r.watched_seconds for r in await _movie_rows(db_session)] == [20, 35]


async def test_a_closed_row_without_its_last_second_proves_nothing():
    reports._writers.add(("Web", "Films"))
    reports._saving_devices.add("DEVICE-1")
    _library_saves_from(3)
    reports._last_stored["k"] = reports._LastStored(0, T0)
    closed = SimpleNamespace(library_name="Films", last_seen_at=None, position_ticks=60 * TICK)
    session = emby_session(at=T0 + MIN, position_s=900, runtime_s=1440)
    assert reports.player_is_lost(session, "k", None, closed, StoredPosition(0, False), T0 + MIN) is False


async def test_library_settings_are_read_when_a_saved_position_was(db_session):
    refresh = AsyncMock()
    await poll(db_session, T0, emby_session(at=T0, position_s=60), refresh=refresh)
    refresh.assert_not_awaited()
    await poll(db_session, T0 + STEP, emby_session(at=T0 + STEP, position_s=65), stored=saved(60), refresh=refresh)
    refresh.assert_awaited_once_with("http://emby.test", "k", T0 + STEP)
