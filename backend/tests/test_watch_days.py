"""The days a streak counts: five minutes watched, on the clock of the instance."""
import json
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from constants.playback import WATCH_ITEM_TYPES
from models.playback_stats import PlaybackSession
from services.portal import profile_stats_playback
from services.portal.exclusions import get_exclusion_filters
from services.portal.play_streak import current_streak
from services.portal.watch_days import load_watch_days, watch_days
from services.settings import set_setting
from services.stats_aggregator.records import get_records
from services.watch_hours import spread_over_hours
from tests._stats_local_time_helpers import freeze, play, save_paris, utc

PARIS = ZoneInfo("Europe/Paris")
# 18:00 in Paris on 2 October, the 124th day of the long run.
LONG_RUN_NOW = utc(2026, 10, 2, 16)


class _Frozen(datetime):
    @classmethod
    def now(cls, tz=None):
        return LONG_RUN_NOW


def _play(started: datetime, seconds: int, item_type: str = "Movie") -> PlaybackSession:
    """A play as the collector leaves it: only films and episodes keep their seconds per hour."""
    return PlaybackSession(
        item_type=item_type,
        started_at=started,
        watched_seconds=seconds,
        watched_by_hour=spread_over_hours(started, seconds) if item_type in WATCH_ITEM_TYPES else None,
    )


def test_a_film_finished_after_midnight_fills_the_next_day():
    """23:30 to 00:15 in Paris, nothing started on the 25th: the 25th counts there, not in UTC."""
    film = _play(utc(2026, 9, 24, 21, 30), 45 * 60)

    assert watch_days([film], PARIS) == {date(2026, 9, 24), date(2026, 9, 25)}
    assert watch_days([film], UTC) == {date(2026, 9, 24)}


def test_a_launch_of_two_minutes_fills_no_day():
    assert watch_days([_play(utc(2026, 10, 14, 12), 2 * 60)], PARIS) == set()


@pytest.mark.parametrize(("seconds", "counts"), [(4 * 60 + 59, False), (5 * 60, True)])
def test_five_minutes_make_a_day_across_two_hours(seconds, counts):
    """From 13:58 in Paris: two minutes in one hour, the rest in the next, added up."""
    days = watch_days([_play(utc(2026, 10, 14, 11, 58), seconds)], PARIS)

    assert days == ({date(2026, 10, 14)} if counts else set())


@pytest.mark.parametrize(("past_midnight", "days"), [
    (0, {9}),
    (4 * 60 + 59, {9}),
    (5 * 60, {9, 10}),
])
def test_midnight_sharp_opens_the_next_day(past_midnight, days):
    """Paris is UTC+1 in January: a film from 22:00 to midnight, then a little more."""
    film = _play(utc(2026, 1, 9, 21), 2 * 3600 + past_midnight)

    assert watch_days([film], PARIS) == {date(2026, 1, day) for day in days}


@pytest.mark.parametrize(("zone", "day"), [
    ("UTC", 14),
    ("Europe/Paris", 15),
    ("Pacific/Auckland", 15),
    ("America/New_York", 14),
])
def test_the_hours_are_dated_on_the_clock_of_the_instance(zone, day):
    """22:00 UTC on 14 October: midnight in Paris, morning in Auckland, evening in New York."""
    assert watch_days([_play(utc(2026, 10, 14, 22), 10 * 60)], ZoneInfo(zone)) == {date(2026, 10, day)}


def test_a_pause_counts_for_nothing():
    """Three hours on screen, two minutes played: only the measured time counts."""
    paused = PlaybackSession(
        item_type="Movie",
        started_at=utc(2026, 10, 14, 18),
        ended_at=utc(2026, 10, 14, 21),
        watched_seconds=2 * 60,
        watched_by_hour={"2026-10-14T18": 2 * 60},
    )

    assert watch_days([paused], PARIS) == set()


@pytest.mark.parametrize("item_type", ["Audio", "AudioBook"])
def test_music_and_audiobooks_count_for_nothing(item_type):
    assert watch_days([_play(utc(2026, 10, 14, 12), 3600, item_type)], PARIS) == set()


@pytest.mark.parametrize("item_type", ["Video", "TvChannel"])
def test_other_video_counts_from_its_watched_time(item_type):
    """Kept per title only, its time is laid from its start: 23:58 to 00:08 in Paris."""
    clip = _play(utc(2026, 10, 14, 21, 58), 10 * 60, item_type)

    assert watch_days([clip], PARIS) == {date(2026, 10, 15)}


def test_a_day_without_enough_watching_breaks_the_run():
    days = watch_days([
        _play(utc(2026, 10, 14, 12), 10 * 60),
        _play(utc(2026, 10, 15, 12), 2 * 60),
        _play(utc(2026, 10, 16, 12), 10 * 60),
    ], PARIS)

    assert days == {date(2026, 10, 14), date(2026, 10, 16)}
    assert current_streak(days, date(2026, 10, 16)) == 1


@pytest.mark.asyncio
async def test_excluded_titles_fill_no_day(db_session):
    await set_setting(
        db_session, "stats.exclusions", json.dumps([{"mode": "exact", "value": "Test Intro"}]),
    )
    play(db_session, utc(2026, 10, 14, 12), item="Test Intro", watched=3600, exclusive=3600)
    play(db_session, utc(2026, 10, 15, 12), watched=600, exclusive=600)
    await db_session.commit()

    filters = [PlaybackSession.user_name == "alice", *await get_exclusion_filters(db_session)]

    assert await load_watch_days(db_session, filters, PARIS) == {date(2026, 10, 15)}


@pytest.mark.asyncio
async def test_a_long_run_of_late_films_keeps_every_day(db_session, monkeypatch):
    """124 days in Paris: a film each evening until 00:30, nothing started every tenth day."""
    first = utc(2026, 6, 1, 20, 30)  # 22:30 in Paris, summer time
    for n in range(123):
        if n % 10 != 5:
            play(db_session, first + timedelta(days=n), watched=2 * 3600, exclusive=2 * 3600)
    await db_session.commit()
    freeze(monkeypatch, LONG_RUN_NOW)
    monkeypatch.setattr(profile_stats_playback, "datetime", _Frozen)
    await save_paris(db_session)

    players = PlaybackSession.user_name == "alice"
    assert await profile_stats_playback.compute_streak(db_session, players, [], PARIS) == 124
    stats = await get_records(db_session)
    assert (stats["current_streak"], stats["longest_streak"]) == (124, 124)
