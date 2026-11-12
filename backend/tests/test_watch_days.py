"""The days a streak counts: those holding watched time, on the clock of the instance."""
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from models.playback_stats import PlaybackSession
from services.portal import profile_stats_playback
from services.portal.play_streak import current_streak
from services.portal.watch_days import watch_days
from services.stats_aggregator.records import get_records
from services.stats_collector._measure import spread_over_hours
from tests._stats_local_time_helpers import freeze, play, save_paris, utc

PARIS = ZoneInfo("Europe/Paris")
# 18:00 in Paris on 2 October, the 124th day of the long run.
LONG_RUN_NOW = utc(2026, 10, 2, 16)


class _Frozen(datetime):
    @classmethod
    def now(cls, tz=None):
        return LONG_RUN_NOW


def test_a_film_finished_after_midnight_fills_the_next_day():
    """23:30 to 00:15 in Paris, nothing started on the 25th: the 25th counts there, not in UTC."""
    film = spread_over_hours(utc(2026, 9, 24, 21, 30), 45 * 60)

    assert watch_days([film], PARIS) == {date(2026, 9, 24), date(2026, 9, 25)}
    assert watch_days([film], UTC) == {date(2026, 9, 24)}


def test_midnight_sharp_opens_the_next_day():
    """Paris is UTC+1 in January: a film from 22:00 to midnight sharp stays on its day."""
    until_midnight = spread_over_hours(utc(2026, 1, 9, 21), 2 * 3600)
    past_midnight = spread_over_hours(utc(2026, 1, 9, 21), 2 * 3600 + 5)

    assert watch_days([until_midnight], PARIS) == {date(2026, 1, 9)}
    assert watch_days([past_midnight], PARIS) == {date(2026, 1, 9), date(2026, 1, 10)}


@pytest.mark.parametrize(("zone", "day"), [
    ("UTC", 14),
    ("Europe/Paris", 15),
    ("Pacific/Auckland", 15),
    ("America/New_York", 14),
])
def test_the_hours_are_dated_on_the_clock_of_the_instance(zone, day):
    """22:00 UTC on 14 October: midnight in Paris, morning in Auckland, evening in New York."""
    assert watch_days([{"2026-10-14T22": 600}], ZoneInfo(zone)) == {date(2026, 10, day)}


def test_a_day_without_watching_breaks_the_run():
    """Music, or a title stopped before its first second, keeps no watched hour."""
    days = watch_days([
        spread_over_hours(utc(2026, 10, 14, 12), 600),
        None,
        {},
        spread_over_hours(utc(2026, 10, 16, 12), 600),
    ], PARIS)

    assert days == {date(2026, 10, 14), date(2026, 10, 16)}
    assert current_streak(days, date(2026, 10, 16)) == 1


@pytest.mark.asyncio
async def test_a_long_run_of_late_films_keeps_every_day(db_session, monkeypatch):
    """124 days in Paris: a film each evening until 00:30, nothing started every tenth day."""
    first = utc(2026, 6, 1, 20, 30)  # 22:30 in Paris, summer time
    for n in range(123):
        if n % 10 != 5:
            play(db_session, first + timedelta(days=n), exclusive=2 * 3600)
    await db_session.commit()
    freeze(monkeypatch, LONG_RUN_NOW)
    monkeypatch.setattr(profile_stats_playback, "datetime", _Frozen)
    await save_paris(db_session)

    players = PlaybackSession.user_name == "alice"
    assert await profile_stats_playback.compute_streak(db_session, players, [], PARIS) == 124
    stats = await get_records(db_session)
    assert (stats["current_streak"], stats["longest_streak"]) == (124, 124)
