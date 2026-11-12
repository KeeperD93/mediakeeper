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


def _play(
    started: datetime, seconds: int, item_type: str = "Movie", user: str = "alice",
) -> PlaybackSession:
    """A play as the collector leaves it: only films and episodes keep their seconds per hour."""
    return PlaybackSession(
        user_id=f"emby-{user}",
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


@pytest.mark.parametrize(("zone", "generous", "days"), [
    ("Asia/Kolkata", False, {10}),
    ("Asia/Kolkata", True, {10, 11}),
    ("Europe/Paris", True, {10}),
])
def test_a_generous_count_gives_an_hour_across_midnight_to_both_days(zone, generous, days):
    """18:20 to 18:55 UTC: 23:50 to 00:25 in Kolkata (UTC+5:30), 19:20 to 19:55 in Paris."""
    film = _play(utc(2026, 1, 10, 18, 20), 35 * 60)

    assert watch_days([film], ZoneInfo(zone), generous=generous) == {date(2026, 1, day) for day in days}


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


@pytest.mark.parametrize(("second_start", "counts"), [(0, False), (150, True)])
def test_two_videos_of_one_account_at_once_count_once(second_start, counts):
    """Two and a half minutes on each: at the same time they make 2:30, one after the other 5:00."""
    noon = utc(2026, 10, 14, 12)
    clips = [_play(noon, 150, "Video"), _play(noon + timedelta(seconds=second_start), 150, "Video")]

    assert watch_days(clips, PARIS) == ({date(2026, 10, 14)} if counts else set())


@pytest.mark.parametrize(("minutes", "days"), [(12, {14}), (13, {14, 15})])
def test_only_the_union_of_overlapping_videos_counts(minutes, days):
    """From 23:50 to 00:02 in Paris, and from 23:52: after midnight only what the second adds."""
    first = _play(utc(2026, 10, 14, 21, 50), 12 * 60, "Video")
    second = _play(utc(2026, 10, 14, 21, 52), minutes * 60, "Video")

    assert watch_days([first, second], PARIS) == {date(2026, 10, day) for day in days}


def test_two_accounts_at_once_are_never_merged():
    """Alice and Bob, two and a half minutes each at noon: the instance watched five."""
    noon = utc(2026, 10, 14, 12)
    clips = [_play(noon, 150, "Video", "alice"), _play(noon, 150, "Video", "bob")]

    assert watch_days(clips, PARIS) == {date(2026, 10, 14)}


def test_films_keep_their_hours_and_music_stays_apart():
    """A film resumed the next morning counts then; music beside a video adds nothing."""
    film = PlaybackSession(
        item_type="Movie",
        started_at=utc(2026, 10, 14, 12),
        watched_seconds=10 * 60,
        watched_by_hour={"2026-10-15T08": 10 * 60},
    )
    clip = _play(utc(2026, 10, 16, 12), 3 * 60, "Video")
    song = _play(utc(2026, 10, 16, 12, 2), 3 * 60, "Audio")

    assert watch_days([film, clip, song], PARIS) == {date(2026, 10, 15)}


@pytest.mark.parametrize(("second_minute", "days"), [(40, {10, 11}), (21, set())])
def test_a_generous_count_merges_too_and_loses_no_day(second_minute, days):
    """Three minutes from 23:50 in Kolkata, three more apart or overlapping: the hour across
    midnight gives both days six minutes, or nothing once they make four."""
    first = _play(utc(2026, 1, 10, 18, 20), 3 * 60, "Video")
    second = _play(utc(2026, 1, 10, 18, second_minute), 3 * 60, "Video")

    days_watched = watch_days([first, second], ZoneInfo("Asia/Kolkata"), generous=True)
    assert days_watched == {date(2026, 1, day) for day in days}


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
async def test_the_profile_merges_one_account_and_the_records_never_two(db_session):
    """Alice plays two videos at noon, Bob one, 2:30 each: Alice's day holds 2:30, the instance's 5."""
    noon = utc(2026, 10, 14, 12)
    for user, item in (("alice", "Test Clip"), ("alice", "Test Clip 2"), ("bob", "Test Clip")):
        db_session.add(PlaybackSession(
            session_key=f"{user}-{item}", user_id=f"emby-{user}", user_name=user,
            item_id=item, item_name=item, item_type="Video", started_at=noon, watched_seconds=150,
        ))
    await db_session.commit()
    await save_paris(db_session)

    assert await load_watch_days(db_session, [PlaybackSession.user_name == "alice"], PARIS) == set()
    assert (await get_records(db_session))["longest_streak"] == 1


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
