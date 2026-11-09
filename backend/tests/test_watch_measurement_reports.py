"""A player gone while Emby keeps moving its session: what counts, and when the row ends."""
from datetime import timedelta
from types import SimpleNamespace

import pytest

from services.stats_collector import _player_reports as reports
from services.stats_collector._measure import as_utc
from services.stats_collector._player_reports import StoredPosition, player_is_lost
from tests._watch_measurement_helpers import (
    STEP,
    T0,
    TICK,
    completions,
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


async def test_a_lost_player_stops_counting(db_session):
    last, position, position_saved = await play_reporting(db_session, 2000, 25)
    await emby_alone(db_session, last, position, position_saved, 40)
    (row,) = await rows(db_session)
    # 120 s played, then only what passes before the session is 30 s from the saved position.
    assert row.watched_seconds == 147
    assert row.position_ticks < (position + 35) * TICK
    assert as_utc(row.last_seen_at) < last + timedelta(seconds=40)


async def test_what_the_buffer_played_counts_when_the_player_is_back(db_session):
    last, position, position_saved = await play_reporting(db_session, 2000, 25)
    held, _ = await emby_alone(db_session, last, position, position_saved, 30)
    back = held + STEP
    await poll(db_session, back, emby_session(at=back, position_s=position + 60), stored=saved(position + 58))
    (row,) = await rows(db_session)
    assert row.watched_seconds == 120 + 60


async def test_an_application_that_never_saves_keeps_the_activity_rule(db_session):
    # Saved position frozen where the viewing started: nothing proves this application reports it.
    for i in range(120):
        at = T0 + STEP * i
        await poll(db_session, at, emby_session(at=at, position_s=2880 + 5 * i), stored=saved(2880))
    (row,) = await rows(db_session)
    assert row.watched_seconds == 595
    assert not reports._writers


async def test_a_saved_position_that_stays_out_of_reach_proves_nothing(db_session):
    # Known application, new title, saved position left far away by an earlier viewing.
    await play_reporting(db_session, 1000, 4, item="OTHER", session="S-0")
    for i in range(60):
        at = T0 + timedelta(hours=1) + STEP * i
        await poll(db_session, at, emby_session(at=at, position_s=2000 + 5 * i), stored=saved(5000))
    new = (await rows(db_session))[-1]
    assert new.watched_seconds == 295


async def test_a_young_row_is_not_judged_on_an_old_saved_position(db_session):
    # Known application, a saved position 20 s ahead that this viewing has not rewritten yet.
    await play_reporting(db_session, 1000, 4, item="OTHER", session="S-0")
    for i in range(30):
        at = T0 + timedelta(hours=1) + STEP * i
        await poll(db_session, at, emby_session(at=at, position_s=2000 + 5 * i), stored=saved(2020))
    new = (await rows(db_session))[-1]
    assert new.watched_seconds == 145


async def test_a_saved_position_moving_far_away_proves_nothing_about_the_application(db_session):
    # Saved by another device of the account: it moves, but never where this session plays.
    for i in range(6):
        at = T0 + STEP * i
        await poll(db_session, at, emby_session(at=at, position_s=1000 + 5 * i), stored=saved(5000 + 10 * (i // 2)))
    assert not reports._writers


@pytest.mark.parametrize("kw", [{"paused": True}, {"item": "SONG-1", "item_type": "Audio"}])
async def test_only_a_playing_video_can_be_lost(kw):
    reports._writers.add(("Web", "Films"))
    row = SimpleNamespace(library_name="Films", last_tick_at=T0 - timedelta(minutes=5))
    assert player_is_lost(emby_session(at=T0, position_s=60, **kw), "k", row, None, None, T0) is False


async def test_a_failed_read_does_not_release_a_held_row(db_session):
    last, position, position_saved = await play_reporting(db_session, 2000, 25)
    held, moved = await emby_alone(db_session, last, position, position_saved, 30)
    failed = held + STEP
    await poll(db_session, failed, emby_session(at=failed, position_s=moved + 4.5))
    await emby_alone(db_session, failed, moved + 4.5, position_saved, 10)
    (row,) = await rows(db_session)
    assert row.watched_seconds == 147


async def test_a_failed_read_during_normal_playback_loses_nothing(db_session):
    last, position, _ = await play_reporting(db_session, 2000, 25)
    at = last + STEP
    await poll(db_session, at, emby_session(at=at, position_s=position + 5))
    (row,) = await rows(db_session)
    assert row.watched_seconds == 125


async def test_saved_at_zero_far_into_a_film_means_the_player_is_lost(db_session):
    await play_reporting(db_session, 1000, 4, item="OTHER", session="S-0")
    start = T0 + timedelta(hours=1)
    for i in range(8):
        at = start + STEP * i
        await poll(db_session, at, emby_session(at=at, position_s=700 + 5 * i, runtime_s=7200), stored=saved(0))
    (row,) = [r for r in await rows(db_session) if r.item_id == "MOVIE-1"]
    # 10 % of the film is 720 s: nothing counts from there.
    assert row.watched_seconds == 15


@pytest.mark.parametrize("runtime, played, expected", [
    (1800, False, 35),  # a short title may never get a resume position
    (7200, True, 35),   # at 0 and marked played: past the end of the resume zone
])
async def test_saved_at_zero_proves_nothing_elsewhere(db_session, runtime, played, expected):
    await play_reporting(db_session, 1000, 4, item="OTHER", session="S-0")
    start = T0 + timedelta(hours=1)
    for i in range(8):
        at = start + STEP * i
        await poll(db_session, at, emby_session(at=at, position_s=700 + 5 * i, runtime_s=runtime), stored=saved(0, played=played))
    (row,) = [r for r in await rows(db_session) if r.item_id == "MOVIE-1"]
    assert row.watched_seconds == expected


async def test_an_application_is_known_per_library(db_session):
    await play_reporting(db_session, 1000, 4, client="Theater")
    assert reports._writers == {("Theater", "Films")}


@pytest.mark.parametrize("event", ["pause", "seek"])
async def test_one_save_at_a_pause_or_a_seek_proves_nothing(db_session, event):
    # This application saves its position only when the viewer pauses or seeks.
    for i in range(12):
        at, position = T0 + STEP * i, 700 + 5 * i
        await poll(db_session, at, emby_session(at=at, position_s=position, runtime_s=7200), stored=saved(0))
    if event == "pause":
        at += STEP
        await poll(db_session, at, emby_session(at=at, position_s=position, paused=True, runtime_s=7200))
    else:
        position += 300
    for i in range(1, 25):
        at += STEP
        position += 5
        await poll(db_session, at, emby_session(at=at, position_s=position, runtime_s=7200), stored=saved(755 if event == "pause" else 1055))
    assert not reports._writers


async def test_saves_at_two_close_pauses_prove_nothing(db_session):
    # Both saves are near each other and near the session, but neither comes from a report while playing.
    at = T0
    for saved_at_pause, position in ((700, 700), (720, 720)):
        await poll(db_session, at, emby_session(at=at, position_s=position, paused=True))
        for i in range(1, 5):
            at += STEP
            await poll(db_session, at, emby_session(at=at, position_s=position + 5 * i), stored=saved(saved_at_pause))
        at += STEP
    assert not reports._writers


async def test_a_first_read_proves_nothing(db_session):
    await poll(db_session, T0, emby_session(at=T0, position_s=2000))
    at = T0 + STEP
    await poll(db_session, at, emby_session(at=at, position_s=2005), stored=saved(2003))
    assert not reports._writers


async def test_an_application_is_only_trusted_in_the_library_where_it_was_seen():
    reports._writers.add(("Web", "Films"))
    far_session = emby_session(at=T0, position_s=2100)
    def row(library):
        return SimpleNamespace(library_name=library, watched_seconds=120, position_ticks=2000 * TICK, last_tick_at=T0)
    assert player_is_lost(far_session, "k", row("Films"), None, StoredPosition(2000 * TICK, False), T0) is True
    assert player_is_lost(far_session, "k", row("Series"), None, StoredPosition(2000 * TICK, False), T0) is False


async def test_a_title_marked_watched_needs_real_viewing(db_session):
    last, position, position_saved = await play_reporting(db_session, 200, 25, runtime_s=600)
    for i in range(1, 80):
        at = last + STEP * i
        await poll(db_session, at, emby_session(at=at, position_s=position + 4.5 * i, runtime_s=600), stored=saved(position_saved))
    assert await completions(db_session) == []


async def test_saved_positions_are_forgotten_with_their_session(db_session):
    last, *_ = await play_reporting(db_session, 2000, 3)
    assert reports._last_stored
    await poll(db_session, last + STEP)
    assert not reports._last_stored
