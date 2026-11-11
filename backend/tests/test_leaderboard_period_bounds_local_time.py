"""Where a leaderboard period starts and how it is named, on the clock of a time zone."""
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from constants.leaderboard import LeaderboardPeriod as Period
from services.instance_time import to_local
from services.portal._leaderboard_periods import (
    days_in_month,
    days_left_in_month,
    period_bounds,
    period_label,
)

PARIS = ZoneInfo("Europe/Paris")
NEW_YORK = ZoneInfo("America/New_York")
HAVANA = ZoneInfo("America/Havana")
KOLKATA = ZoneInfo("Asia/Kolkata")
AUCKLAND = ZoneInfo("Pacific/Auckland")


def _utc(year: int, month: int, day: int, *clock: int) -> datetime:
    return datetime(year, month, day, *clock, tzinfo=UTC)


# 00:30 on Wednesday in Paris, still Tuesday in UTC.
JUST_AFTER_PARIS_MIDNIGHT = _utc(2026, 11, 3, 23, 30)
PARIS_MIDNIGHT = _utc(2026, 11, 3, 23)


@pytest.mark.parametrize(("zone", "now", "period", "start", "previous_start"), [
    (PARIS, JUST_AFTER_PARIS_MIDNIGHT, Period.TODAY, PARIS_MIDNIGHT, _utc(2026, 11, 2, 23)),
    (PARIS, PARIS_MIDNIGHT, Period.TODAY, PARIS_MIDNIGHT, _utc(2026, 11, 2, 23)),
    (PARIS, _utc(2026, 11, 3, 22, 59, 59), Period.TODAY, _utc(2026, 11, 2, 23), _utc(2026, 11, 1, 23)),
    # Summer: midnight is two hours ahead.
    (PARIS, _utc(2026, 7, 14, 22, 30), Period.TODAY, _utc(2026, 7, 14, 22), _utc(2026, 7, 13, 22)),
    # The day before lasted 25 hours, then 23: only the clock tells where it started.
    (PARIS, _utc(2026, 10, 26, 12), Period.TODAY, _utc(2026, 10, 25, 23), _utc(2026, 10, 24, 22)),
    (PARIS, _utc(2026, 3, 30, 12), Period.TODAY, _utc(2026, 3, 29, 22), _utc(2026, 3, 28, 23)),
    # A week across the clock change, then Sunday night in UTC, already Monday in Paris.
    (PARIS, _utc(2026, 10, 28, 12), Period.WEEK, _utc(2026, 10, 25, 23), _utc(2026, 10, 18, 22)),
    (PARIS, _utc(2026, 11, 8, 23, 30), Period.WEEK, _utc(2026, 11, 8, 23), _utc(2026, 11, 1, 23)),
    # A month across the clock change, its first hour, and a month across two years.
    (PARIS, _utc(2026, 11, 15, 12), Period.MONTH, _utc(2026, 10, 31, 23), _utc(2026, 9, 30, 22)),
    (PARIS, _utc(2026, 10, 31, 23, 30), Period.MONTH, _utc(2026, 10, 31, 23), _utc(2026, 9, 30, 22)),
    (PARIS, _utc(2026, 12, 31, 23, 30), Period.MONTH, _utc(2026, 12, 31, 23), _utc(2026, 11, 30, 23)),
    # West of UTC, the month is not over yet, and a day can end after a clock change.
    (NEW_YORK, _utc(2026, 11, 1, 2), Period.MONTH, _utc(2026, 10, 1, 4), _utc(2026, 9, 1, 4)),
    (NEW_YORK, _utc(2026, 11, 2, 3), Period.TODAY, _utc(2026, 11, 1, 4), _utc(2026, 10, 31, 4)),
    # Offsets that are not whole hours, or a day ahead.
    (KOLKATA, _utc(2026, 11, 3, 18, 30), Period.TODAY, _utc(2026, 11, 3, 18, 30), _utc(2026, 11, 2, 18, 30)),
    (AUCKLAND, _utc(2026, 11, 3, 11), Period.TODAY, _utc(2026, 11, 3, 11), _utc(2026, 11, 2, 11)),
    # Past dates, which new time zone data cannot change. Clocks went back at 01:00 in Havana:
    # 00:30 came twice, and at the second one the day still started at the first midnight.
    (HAVANA, _utc(2025, 11, 2, 5, 30), Period.TODAY, _utc(2025, 11, 2, 4), _utc(2025, 11, 1, 4)),
    # Clocks went forward at midnight in Havana: that day started at 01:00.
    (HAVANA, _utc(2026, 3, 8, 17), Period.TODAY, _utc(2026, 3, 8, 5), _utc(2026, 3, 7, 5)),
])
def test_bounds_on_the_clock_of_the_zone(zone, now, period, start, previous_start):
    bounds = period_bounds(period, to_local(now, zone))

    assert bounds.start == start
    assert bounds.previous_start == previous_start
    # In UTC for real: SQLite would drop any other offset.
    assert bounds.start.tzinfo is UTC
    assert bounds.previous_start.tzinfo is UTC


def test_all_time_has_no_bounds_in_any_zone():
    bounds = period_bounds(Period.ALL, to_local(JUST_AFTER_PARIS_MIDNIGHT, PARIS))

    assert (bounds.start, bounds.previous_start) == (None, None)


@pytest.mark.parametrize(("zone", "now", "days"), [
    (PARIS, _utc(2026, 10, 31, 23, 30), 29),
    (NEW_YORK, _utc(2026, 11, 1, 2), 0),
    # 31 days on the calendar, though the clocks skip an hour on the way.
    (PARIS, _utc(2026, 2, 28, 23), 31),
])
def test_days_left_on_the_calendar_of_the_zone(zone, now, days):
    assert days_left_in_month(to_local(now, zone)) == days


@pytest.mark.parametrize(("zone", "now", "days"), [
    # Already November in Paris, still October in UTC and in New York.
    (PARIS, _utc(2026, 10, 31, 23, 30), 30),
    (UTC, _utc(2026, 10, 31, 23, 30), 31),
    (NEW_YORK, _utc(2026, 11, 1, 2), 31),
    (PARIS, _utc(2028, 2, 10, 12), 29),
    (PARIS, _utc(2027, 2, 10, 12), 28),
])
def test_days_in_the_month_of_the_zone(zone, now, days):
    assert days_in_month(to_local(now, zone)) == days


@pytest.mark.parametrize(("zone", "now", "period", "french", "english"), [
    (PARIS, JUST_AFTER_PARIS_MIDNIGHT, Period.TODAY, "Mercredi 4 novembre", "Wednesday, November 4"),
    (PARIS, _utc(2026, 11, 8, 23, 30), Period.WEEK, "Du 9 au 15 novembre", "November 9–15"),
    (PARIS, _utc(2026, 10, 31, 23, 30), Period.MONTH, "Novembre 2026", "November 2026"),
    (NEW_YORK, _utc(2026, 11, 1, 2), Period.MONTH, "Octobre 2026", "October 2026"),
])
def test_label_on_the_clock_of_the_zone(zone, now, period, french, english):
    local = to_local(now, zone)

    assert period_label(period, local, "fr") == french
    assert period_label(period, local, "en") == english
