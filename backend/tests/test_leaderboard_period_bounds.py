"""Where each leaderboard period starts, and how it is named, on fixed dates."""
from datetime import UTC, datetime

import pytest

from constants.leaderboard import LeaderboardPeriod as Period
from services.portal._leaderboard_periods import (
    days_left_in_month,
    period_bounds,
    period_label,
)


def _at(year: int, month: int, day: int, *clock: int) -> datetime:
    return datetime(year, month, day, *clock, tzinfo=UTC)


WEDNESDAY = _at(2026, 11, 4, 15, 30, 45, 123)


@pytest.mark.parametrize(("now", "period", "start", "previous_start"), [
    (WEDNESDAY, Period.TODAY, _at(2026, 11, 4), _at(2026, 11, 3)),
    (_at(2026, 3, 1, 0, 0, 0), Period.TODAY, _at(2026, 3, 1), _at(2026, 2, 28)),
    (_at(2027, 1, 1, 23, 59, 59), Period.TODAY, _at(2027, 1, 1), _at(2026, 12, 31)),
    (WEDNESDAY, Period.WEEK, _at(2026, 11, 2), _at(2026, 10, 26)),
    # The first and the last moment of a week, Monday to Sunday.
    (_at(2026, 11, 2, 0, 0, 0), Period.WEEK, _at(2026, 11, 2), _at(2026, 10, 26)),
    (_at(2026, 11, 8, 23, 59, 59), Period.WEEK, _at(2026, 11, 2), _at(2026, 10, 26)),
    # A week across two years.
    (_at(2027, 1, 1, 12), Period.WEEK, _at(2026, 12, 28), _at(2026, 12, 21)),
    (WEDNESDAY, Period.MONTH, _at(2026, 11, 1), _at(2026, 10, 1)),
    (_at(2026, 3, 31, 23, 59, 59), Period.MONTH, _at(2026, 3, 1), _at(2026, 2, 1)),
    (_at(2027, 1, 15), Period.MONTH, _at(2027, 1, 1), _at(2026, 12, 1)),
    (WEDNESDAY, Period.ALL, None, None),
])
def test_bounds_of_each_period(now, period, start, previous_start):
    bounds = period_bounds(period, now)

    assert bounds.start == start
    assert bounds.previous_start == previous_start


@pytest.mark.parametrize(("now", "days"), [
    (WEDNESDAY, 26),
    (_at(2026, 12, 31, 23, 59, 59), 0),
    (_at(2026, 12, 1), 31),
    (_at(2028, 2, 10, 12), 19),
    (_at(2027, 2, 10, 12), 18),
])
def test_days_left_in_the_month(now, days):
    assert days_left_in_month(now) == days


@pytest.mark.parametrize(("now", "period", "french", "english"), [
    (WEDNESDAY, Period.TODAY, "Mercredi 4 novembre", "Wednesday, November 4"),
    (_at(2026, 11, 1), Period.TODAY, "Dimanche 1er novembre", "Sunday, November 1"),
    (_at(2026, 11, 2), Period.TODAY, "Lundi 2 novembre", "Monday, November 2"),
    (WEDNESDAY, Period.WEEK, "Du 2 au 8 novembre", "November 2–8"),
    (_at(2027, 3, 3), Period.WEEK, "Du 1er au 7 mars", "March 1–7"),
    (_at(2026, 12, 2), Period.WEEK, "Du 30 novembre au 6 décembre", "November 30 – December 6"),
    (_at(2026, 10, 28), Period.WEEK, "Du 26 octobre au 1er novembre", "October 26 – November 1"),
    (_at(2027, 1, 1), Period.WEEK, "Du 28 décembre au 3 janvier", "December 28 – January 3"),
    (WEDNESDAY, Period.MONTH, "Novembre 2026", "November 2026"),
    (WEDNESDAY, Period.ALL, "Depuis le début", "Since the beginning"),
])
def test_label_of_each_period(now, period, french, english):
    assert period_label(period, now, "fr") == french
    assert period_label(period, now, "en") == english
