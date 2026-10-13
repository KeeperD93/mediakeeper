"""Continuous watch-time measurement: what the collector counts, poll by poll."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackCompletion, PlaybackSession
from services.stats_collector._measure import (
    as_utc,
    client_is_alive,
    exclusive_shares,
    history_measure,
    parse_emby_date,
    progress_seconds,
    spread_over_hours,
)
from services.stats_collector.collect import collect_active_sessions

TICK = 10_000_000
T0 = datetime(2026, 3, 7, 20, 0, tzinfo=timezone.utc)


def _emby_date(at: datetime) -> str:
    # Emby writes 7 fractional digits and a trailing Z.
    return at.strftime("%Y-%m-%dT%H:%M:%S.%f") + "0Z"


def _session(
    *, at: datetime, position_s: float, paused: bool = False, item: str = "MOVIE-1",
    item_type: str = "Movie", runtime_s: int = 6000, user: str = "EMBY-1",
    session: str = "S-1", silent_since: datetime | None = None,
) -> dict:
    return {
        "Id": session,
        "UserId": user,
        "UserName": "viewer",
        "Client": "Web",
        "DeviceName": "PC",
        "LastActivityDate": _emby_date(silent_since or at),
        "NowPlayingItem": {
            "Id": item, "Name": "Sample title", "Type": item_type, "RunTimeTicks": runtime_s * TICK,
        },
        "PlayState": {"IsPaused": paused, "PositionTicks": int(position_s * TICK)},
    }


async def _poll(db, at: datetime, *sessions: dict) -> None:
    source = {"source": "emby", "url": "http://emby.test", "api_key": "k"}
    with patch("services.stats_collector.collect.get_active_media_source", new=AsyncMock(return_value=source)), \
         patch("services.stats_collector.collect.get_raw_sessions", new=AsyncMock(return_value=list(sessions))), \
         patch("services.stats_collector.collect._session_library_name", new=AsyncMock(return_value="Films")), \
         patch("services.stats_collector.collect._grant_post_session_xp", new=AsyncMock()):
        await collect_active_sessions(db, now=at)


async def _rows(db) -> list[PlaybackSession]:
    query = select(PlaybackSession).order_by(PlaybackSession.id).execution_options(populate_existing=True)
    return (await db.execute(query)).scalars().all()


async def _completions(db) -> list[PlaybackCompletion]:
    return (await db.execute(select(PlaybackCompletion))).scalars().all()


async def _play(db, start: datetime, positions: list[float], step: timedelta, **kw) -> datetime:
    """One poll per position, ``step`` apart; returns the time of the last poll."""
    at = start
    for i, position in enumerate(positions):
        at = start + step * i
        await _poll(db, at, _session(at=at, position_s=position, **kw))
    return at


@pytest.mark.asyncio
async def test_real_playback_is_counted_poll_by_poll(db_session):
    # Players often report the start late: 25 s already played at the first poll.
    await _play(db_session, T0, [25, 30, 35, 40], timedelta(seconds=5))
    (row,) = await _rows(db_session)
    assert row.watched_seconds == 40 and row.exclusive_seconds == 40
    assert row.measured is True
    # The seconds played before the first poll count, and the start is moved back.
    assert as_utc(row.started_at) == T0 - timedelta(seconds=25)


@pytest.mark.asyncio
async def test_pause_and_frozen_position_add_nothing(db_session):
    # Resumed at 10 min: what was watched before is not credited again.
    await _play(db_session, T0, [600, 605], timedelta(seconds=5))
    for minute in (1, 2, 3):
        at = T0 + timedelta(minutes=minute)
        await _poll(db_session, at, _session(at=at, position_s=605, paused=True))
    resume = T0 + timedelta(minutes=3, seconds=5)
    await _poll(db_session, resume, _session(at=resume, position_s=610))
    (row,) = await _rows(db_session)
    assert row.watched_seconds == 10


@pytest.mark.asyncio
async def test_seek_forward_only_counts_the_time_spent(db_session):
    await _play(db_session, T0, [5, 2400], timedelta(seconds=5))
    (row,) = await _rows(db_session)
    assert row.watched_seconds == 10


@pytest.mark.asyncio
async def test_silent_player_adds_nothing_even_if_emby_keeps_advancing(db_session):
    last_live = await _play(db_session, T0, [5, 10], timedelta(seconds=5))
    # TV switched off without leaving Emby: the session stays listed as
    # playing and Emby keeps moving the position, but the player is silent.
    for i in (1, 2, 3):
        at = last_live + timedelta(minutes=3 * i)
        await _poll(db_session, at, _session(at=at, position_s=10 + 180 * i, silent_since=last_live))
    (row,) = await _rows(db_session)
    assert row.watched_seconds == 10
    assert as_utc(row.last_seen_at) == last_live
    assert row.position_ticks == 10 * TICK  # the extrapolated position is not "reached"

    # Switched back on: the player reports its own position, where it stopped.
    back = last_live + timedelta(minutes=9, seconds=5)
    await _poll(db_session, back, _session(at=back, position_s=15))
    (row,) = await _rows(db_session)
    assert row.watched_seconds == 15
    assert as_utc(row.last_seen_at) == back


@pytest.mark.asyncio
async def test_a_player_lost_mid_playback_is_not_counted_while_emby_keeps_going(db_session):
    # The network drops: Emby keeps the session and moves the position on its
    # own, but the player sends nothing more until Emby drops the session.
    last_live = await _play(db_session, T0, [5, 10, 15], timedelta(seconds=5))
    for i in (1, 2, 3, 4):
        at = last_live + timedelta(seconds=5 * i)
        await _poll(db_session, at, _session(at=at, position_s=15 + 5 * i, silent_since=last_live))
    await _poll(db_session, last_live + timedelta(seconds=25))
    (row,) = await _rows(db_session)
    assert row.watched_seconds == 15
    assert row.is_active is False and as_utc(row.ended_at) == last_live


@pytest.mark.asyncio
async def test_what_a_player_played_from_its_buffer_counts_when_it_reports_again(db_session):
    # Network cut: the player keeps playing its buffer while it cannot report,
    # Emby moves the position on its own, then drops the session.
    last_live = await _play(db_session, T0, [5, 10, 15], timedelta(seconds=5))
    for i in range(1, 13):
        at = last_live + timedelta(seconds=5 * i)
        await _poll(db_session, at, _session(at=at, position_s=15 + 5 * i, silent_since=last_live))
    await _poll(db_session, last_live + timedelta(seconds=65))
    # Network back: the player reports where its buffer ran out, 90 s further.
    back = last_live + timedelta(minutes=2, seconds=30)
    await _poll(db_session, back, _session(at=back, position_s=105))
    (row,) = await _rows(db_session)
    assert row.watched_seconds == 15 + 90


@pytest.mark.asyncio
async def test_a_player_reporting_less_often_loses_nothing(db_session):
    # This player reports every 15 s while the collector polls every 5 s.
    last_report = T0
    for i in range(7):
        at = T0 + timedelta(seconds=5 * i)
        if i % 3 == 0:
            last_report = at
        await _poll(db_session, at, _session(at=at, position_s=5 + 5 * i, silent_since=last_report))
    (row,) = await _rows(db_session)
    assert row.watched_seconds == 35


@pytest.mark.asyncio
async def test_a_new_row_is_opened_for_each_playback(db_session):
    await _play(db_session, T0, [5, 10], timedelta(seconds=5))
    await _poll(db_session, T0 + timedelta(seconds=10))  # stopped: the session is gone
    later = T0 + timedelta(hours=20)
    await _poll(db_session, later, _session(at=later, position_s=12))
    first, second = await _rows(db_session)
    assert first.is_active is False and second.is_active is True
    assert first.emby_session_key == second.emby_session_key
    assert first.session_key != second.session_key
    # The first row is not stretched over the 20 hours between the two plays.
    assert as_utc(first.ended_at) == T0 + timedelta(seconds=5)


@pytest.mark.asyncio
async def test_a_pause_that_makes_emby_drop_the_session_keeps_one_row(db_session):
    await _play(db_session, T0, [5, 10], timedelta(seconds=5))
    # Paused: this player makes Emby drop the session after about a minute.
    for seconds in (10, 60, 120, 180):
        await _poll(db_session, T0 + timedelta(seconds=seconds))
    resume = T0 + timedelta(minutes=3, seconds=5)
    await _poll(db_session, resume, _session(at=resume, position_s=15))
    (row,) = await _rows(db_session)
    assert row.is_active is True and row.ended_at is None
    assert row.watched_seconds == 15  # 10 before the pause, 5 after, nothing during


@pytest.mark.asyncio
async def test_relaunch_from_the_start_after_closing_the_player(db_session):
    # 2 min, a 30 s pause, 30 s more, then the player is closed (Emby forgets
    # positions under its resume threshold) and the title is relaunched from 0.
    first = [5 + 5 * i for i in range(24)]                       # 0:05 -> 2:00
    end_first = await _play(db_session, T0, first, timedelta(seconds=5))
    pause_end = end_first + timedelta(seconds=30)
    for at in (end_first + timedelta(seconds=10), end_first + timedelta(seconds=20), pause_end):
        await _poll(db_session, at, _session(at=at, position_s=120, paused=True))
    second_start = pause_end + timedelta(seconds=5)
    end_second = await _play(db_session, second_start, [125 + 5 * i for i in range(6)], timedelta(seconds=5))
    await _poll(db_session, end_second + timedelta(seconds=5))   # window closed
    relaunch = end_second + timedelta(minutes=1, seconds=30)
    await _play(db_session, relaunch, [20, 25, 30], timedelta(seconds=5))
    (row,) = await _rows(db_session)
    # 120 s + 30 s + 30 s really played; the pause adds nothing.
    assert row.watched_seconds == 120 + 30 + 30


@pytest.mark.asyncio
async def test_relaunching_a_finished_title_is_not_a_rewatch_until_watched_again(db_session):
    full = [5 + 60 * i for i in range(11)]
    finished = await _play(db_session, T0, full, timedelta(minutes=1), runtime_s=600)
    await _poll(db_session, finished + timedelta(seconds=5))  # credits: the player closes
    restart = finished + timedelta(minutes=2)
    await _play(db_session, restart, [5, 10], timedelta(seconds=5), runtime_s=600)
    first, second = await _rows(db_session)
    assert first.completed_at is not None and first.is_active is False
    assert second.is_active is True and second.watched_seconds == 10
    # Relaunched and stopped: still watched once.
    assert len(await _completions(db_session)) == 1


@pytest.mark.asyncio
async def test_a_title_watched_twice_to_the_end_counts_twice(db_session):
    full = [5 + 60 * i for i in range(11)]
    finished = await _play(db_session, T0, full, timedelta(minutes=1), runtime_s=600)
    await _poll(db_session, finished + timedelta(seconds=5))
    again = finished + timedelta(hours=1)
    await _play(db_session, again, full, timedelta(minutes=1), runtime_s=600)
    assert len(await _completions(db_session)) == 2


@pytest.mark.asyncio
async def test_two_devices_count_once_for_the_user(db_session):
    for i, (movie_pos, episode_pos) in enumerate([(5, 3), (10, 8), (15, 13)]):
        at = T0 + timedelta(seconds=5 * i)
        await _poll(
            db_session, at,
            _session(at=at, position_s=movie_pos, item="MOVIE-1", session="S-1"),
            _session(at=at, position_s=episode_pos, item="EP-1", item_type="Episode", session="S-2"),
        )
    rows = await _rows(db_session)
    assert sorted(r.watched_seconds for r in rows) == [13, 15]
    # Per poll the user is credited once: 5 + 5 + 5.
    assert sum(r.exclusive_seconds for r in rows) == 15


@pytest.mark.asyncio
async def test_music_keeps_its_time_but_never_counts_as_watching(db_session):
    await _play(db_session, T0, [5, 10, 15], timedelta(seconds=5), item="SONG-1", item_type="Audio")
    (row,) = await _rows(db_session)
    assert row.watched_seconds == 15
    assert row.exclusive_seconds == 0 and not row.watched_by_hour


@pytest.mark.asyncio
async def test_time_is_filed_under_the_hour_it_was_watched(db_session):
    start = datetime(2026, 3, 7, 20, 59, 55, tzinfo=timezone.utc)
    await _play(db_session, start, [5, 10], timedelta(seconds=5))
    (row,) = await _rows(db_session)
    assert row.watched_by_hour == {"2026-03-07T20": 5, "2026-03-07T21": 5}


@pytest.mark.asyncio
async def test_session_first_seen_paused_or_silent_opens_no_row(db_session):
    await _poll(db_session, T0, _session(at=T0, position_s=3000, paused=True))
    await _poll(db_session, T0, _session(
        at=T0, position_s=4000, session="S-2", silent_since=T0 - timedelta(hours=14),
    ))
    assert await _rows(db_session) == []


@pytest.mark.asyncio
async def test_title_is_watched_once_its_end_is_reached_after_real_viewing(db_session):
    # 10-minute episode watched from the start, one poll per minute.
    positions = [5 + 60 * i for i in range(11)]
    await _play(db_session, T0, positions, timedelta(minutes=1), item_type="Episode", runtime_s=600)
    (row,) = await _rows(db_session)
    (done,) = await _completions(db_session)
    assert done.session_id == row.id and done.source == "live"
    assert done.runtime_seconds == 600 and done.watched_seconds >= 450
    assert row.completed_at is not None


@pytest.mark.asyncio
async def test_seeking_to_the_end_does_not_make_a_title_watched(db_session):
    await _play(db_session, T0, [5, 590, 595, 599], timedelta(seconds=5), runtime_s=600)
    assert await _completions(db_session) == []


@pytest.mark.asyncio
async def test_sittings_add_up_to_a_watched_title(db_session):
    # First evening: the first half, then the player is closed.
    await _play(db_session, T0, [5 + 60 * i for i in range(6)], timedelta(minutes=1), runtime_s=600)
    await _poll(db_session, T0 + timedelta(minutes=6))
    assert await _completions(db_session) == []
    # Next day: resumed where it stopped, watched to the end.
    next_day = T0 + timedelta(days=1)
    await _play(db_session, next_day, [305 + 60 * i for i in range(5)], timedelta(minutes=1), runtime_s=600)
    (done,) = await _completions(db_session)
    assert done.watched_seconds == 305 + 240


def test_emby_dates_with_seven_fraction_digits_are_read():
    assert parse_emby_date("2026-10-13T13:07:51.0194718Z") == datetime(
        2026, 10, 13, 13, 7, 51, 19471, tzinfo=timezone.utc,
    )
    assert parse_emby_date("not a date") is None
    assert parse_emby_date(None) is None


def test_unknown_activity_keeps_the_player_alive():
    assert client_is_alive({}, T0) is True


def test_going_back_in_the_title_adds_nothing():
    assert progress_seconds(600 * TICK, T0, 300 * TICK, T0 + timedelta(seconds=5)) == 0


def test_going_back_to_the_very_start_is_a_restart():
    # Relaunched from the beginning two minutes later, first seen at 0:20.
    assert progress_seconds(152 * TICK, T0, 20 * TICK, T0 + timedelta(minutes=2)) == 20
    # Within a regular poll it can only credit the elapsed time.
    assert progress_seconds(152 * TICK, T0, 20 * TICK, T0 + timedelta(seconds=5)) == 5


def test_duration_only_history_is_laid_out_from_its_start():
    start = datetime(2026, 3, 7, 20, 30, tzinfo=timezone.utc)
    assert spread_over_hours(start, 5400) == {"2026-03-07T20": 1800, "2026-03-07T21": 3600}


def test_history_rows_count_video_only():
    movie = history_measure("k1", "Movie", T0, 3600)
    song = history_measure("k2", "Audio", T0, 3600)
    assert movie["exclusive_seconds"] == 3600 and movie["measured"] is False
    assert song["watched_seconds"] == 3600 and song["exclusive_seconds"] == 0
    assert song["watched_by_hour"] is None


def test_concurrent_progress_goes_to_the_row_that_moved_most():
    shares = exclusive_shares([("a", "u1", 5), ("b", "u1", 3), ("c", "u2", 4), ("d", "u2", 0)])
    assert shares == {"a": 5, "c": 4}
