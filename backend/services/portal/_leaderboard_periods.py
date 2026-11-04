"""Bounds and labels of the leaderboard periods.

Everything reads the calendar of the ``now`` it receives, on the clock of the
instance. Bounds come out in UTC: SQLite would drop any other offset.
"""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from constants.leaderboard import LeaderboardPeriod

MONTH_LABELS_FR = [
    "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]
MONTH_LABELS_EN = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
WEEKDAY_LABELS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
WEEKDAY_LABELS_EN = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]


@dataclass(frozen=True)
class PeriodBounds:
    """``start`` is None for all time, which has no previous period either."""

    start: datetime | None
    previous_start: datetime | None


def _in_utc(start: datetime, previous_start: datetime) -> PeriodBounds:
    return PeriodBounds(start.astimezone(UTC), previous_start.astimezone(UTC))


def period_bounds(period: LeaderboardPeriod, now: datetime) -> PeriodBounds:
    """Return where ``period`` starts around ``now``, and where the one before it starts.

    Python moves a date along its own clock, so a week holds 7 days across a clock change.
    ``fold=0`` takes the first midnight of a night where the clocks go back at that hour.
    """
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0, fold=0)
    match period:
        case LeaderboardPeriod.TODAY:
            return _in_utc(midnight, midnight - timedelta(days=1))
        case LeaderboardPeriod.WEEK:
            monday = midnight - timedelta(days=midnight.weekday())
            return _in_utc(monday, monday - timedelta(days=7))
        case LeaderboardPeriod.MONTH:
            first = midnight.replace(day=1)
            return _in_utc(first, (first - timedelta(days=1)).replace(day=1))
        case LeaderboardPeriod.ALL:
            return PeriodBounds(None, None)


def days_left_in_month(now: datetime) -> int:
    """Whole days left before the next month starts."""
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return ((first + timedelta(days=32)).replace(day=1) - now).days


def _day_fr(moment: datetime) -> str:
    return "1er" if moment.day == 1 else str(moment.day)


def _today_label(now: datetime, french: bool) -> str:
    if french:
        month = MONTH_LABELS_FR[now.month].lower()
        return f"{WEEKDAY_LABELS_FR[now.weekday()]} {_day_fr(now)} {month}"
    return f"{WEEKDAY_LABELS_EN[now.weekday()]}, {MONTH_LABELS_EN[now.month]} {now.day}"


def _week_label(now: datetime, french: bool) -> str:
    monday = now - timedelta(days=now.weekday())
    sunday = monday + timedelta(days=6)
    same_month = monday.month == sunday.month
    if french:
        end_month = MONTH_LABELS_FR[sunday.month].lower()
        if same_month:
            return f"Du {_day_fr(monday)} au {_day_fr(sunday)} {end_month}"
        start_month = MONTH_LABELS_FR[monday.month].lower()
        return f"Du {_day_fr(monday)} {start_month} au {_day_fr(sunday)} {end_month}"
    if same_month:
        return f"{MONTH_LABELS_EN[monday.month]} {monday.day}–{sunday.day}"
    return (
        f"{MONTH_LABELS_EN[monday.month]} {monday.day} – "
        f"{MONTH_LABELS_EN[sunday.month]} {sunday.day}"
    )


def period_label(period: LeaderboardPeriod, now: datetime, lang: str) -> str:
    """Name ``period`` around ``now``: ``Du 2 au 8 novembre`` (FR), ``November 2–8`` (EN)."""
    french = (lang or "fr").startswith("fr")
    match period:
        case LeaderboardPeriod.TODAY:
            return _today_label(now, french)
        case LeaderboardPeriod.WEEK:
            return _week_label(now, french)
        case LeaderboardPeriod.MONTH:
            months = MONTH_LABELS_FR if french else MONTH_LABELS_EN
            return f"{months[now.month]} {now.year}"
        case LeaderboardPeriod.ALL:
            return "Depuis le début" if french else "Since the beginning"
