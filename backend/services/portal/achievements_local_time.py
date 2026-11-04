"""Trophy rules that read the local clock: where an hour and a day start.

One pure function per rule that needs nothing but the plays of a player: they go in, a
progress value comes out, in any zone, with nothing written. Durations stay real seconds,
whatever the clock does on that day. The pass adds the day streak and the lonely new year;
the all-nighter and the king read more rows, in ``playback_algorithms``.
"""
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import date, datetime, timedelta, tzinfo
from typing import NamedTuple

from models.playback_stats import PlaybackSession
from services.instance_time import to_local
from services.portal.achievements_utils import _session_duration_seconds
from services.portal.play_streak import longest_streak

_MOVIE = "Movie"
_EPISODE = "Episode"
_FRIDAY, _SATURDAY, _SUNDAY = 4, 5, 6
_HORROR_GENRES = frozenset({"horror", "horreur"})
_SUMMER_GENRES = frozenset({"adventure", "aventure", "action"})
_SUMMER_MONTHS = (7, 8)
_COUNTDOWN_MINUTES = ((23, 59), (0, 0), (0, 1))
_NEW_YEAR_DAYS = ((12, 31), (1, 1))

_INDECISIVE_MIN_ITEMS = 10
_INDECISIVE_MAX_SECONDS = 30 * 60
_SUNDAY_MIN_SECONDS = 6 * 3600
_BUTTERFLY_MIN_GENRES = 5
_TRIPLE_MIN_MOVIES = 3
_GOURMET_DAYS = 7
_SPEED_RUNNER_MIN_MOVIES = 5
_BINGE_MIN_EPISODES = 10
_MARATHON_MIN_SECONDS = 8 * 3600


class LocalPlay(NamedTuple):
    row: PlaybackSession
    at: datetime


def local_plays(rows: Iterable[PlaybackSession], zone: tzinfo) -> list[LocalPlay]:
    """The rows that have a start, each with that start on the clock of ``zone``."""
    return [LocalPlay(row, to_local(row.started_at, zone)) for row in rows if row.started_at]


def _genres(row: PlaybackSession) -> list[str]:
    return [name.strip() for name in (row.genres or "").split(",") if name.strip()]


def _has_genre(row: PlaybackSession, wanted: frozenset[str]) -> bool:
    return any(name.lower() in wanted for name in _genres(row))


def _rows_by_day(plays: Iterable[LocalPlay]) -> dict[date, list[PlaybackSession]]:
    days: dict[date, list[PlaybackSession]] = defaultdict(list)
    for row, at in plays:
        days[at.date()].append(row)
    return days


def _seconds(rows: Iterable[PlaybackSession]) -> int:
    return sum(_session_duration_seconds(row) for row in rows)


def _days_with_items(plays: Iterable[LocalPlay], item_type: str, minimum: int) -> int:
    """Days holding at least ``minimum`` different titles of ``item_type``."""
    days = _rows_by_day(play for play in plays if play.row.item_type == item_type)
    return sum(len({row.item_id for row in rows}) >= minimum for rows in days.values())


def night_watch(plays: list[LocalPlay]) -> int:
    return sum(at.hour < 5 for _, at in plays)


def early_bird(plays: list[LocalPlay]) -> int:
    return int(any(at.hour == 5 for _, at in plays))


def new_year(plays: list[LocalPlay]) -> int:
    return int(any((at.month, at.day, at.hour) == (1, 1, 0) for _, at in plays))


def friday_13(plays: list[LocalPlay]) -> int:
    return int(any(
        at.day == 13 and at.weekday() == _FRIDAY and _has_genre(row, _HORROR_GENRES)
        for row, at in plays
    ))


def indecisive(plays: list[LocalPlay]) -> int:
    return int(any(
        len({row.item_id for row in rows}) >= _INDECISIVE_MIN_ITEMS
        and max(_session_duration_seconds(row) for row in rows) < _INDECISIVE_MAX_SECONDS
        for rows in _rows_by_day(plays).values()
    ))


def summer(plays: list[LocalPlay]) -> int:
    return int(any(
        at.month in _SUMMER_MONTHS and _has_genre(row, _SUMMER_GENRES)
        for row, at in plays
    ))


def ghost(plays: list[LocalPlay]) -> int:
    return int(any(1 <= at.hour < 4 for _, at in plays))


def countdown(plays: list[LocalPlay]) -> int:
    return int(any((at.hour, at.minute) in _COUNTDOWN_MINUTES for _, at in plays))


def sunday(plays: list[LocalPlay]) -> int:
    sundays = _rows_by_day(play for play in plays if play.at.weekday() == _SUNDAY)
    return int(any(_seconds(rows) >= _SUNDAY_MIN_SECONDS for rows in sundays.values()))


def butterfly(plays: list[LocalPlay]) -> int:
    return int(any(
        len({name for row in rows for name in _genres(row)}) >= _BUTTERFLY_MIN_GENRES
        for rows in _rows_by_day(plays).values()
    ))


def triple(plays: list[LocalPlay]) -> int:
    return int(_days_with_items(plays, _MOVIE, _TRIPLE_MIN_MOVIES) > 0)


def gourmet(plays: list[LocalPlay]) -> int:
    noons = {at.date() for _, at in plays if at.hour == 12}
    return _GOURMET_DAYS if longest_streak(noons) >= _GOURMET_DAYS else 0


def speed_runner(plays: list[LocalPlay]) -> int:
    return _days_with_items(plays, _MOVIE, _SPEED_RUNNER_MIN_MOVIES)


def binge_session(plays: list[LocalPlay]) -> int:
    """Days holding enough different episodes of one series."""
    episodes: dict[tuple[date, str], set[str]] = defaultdict(set)
    for row, at in plays:
        if row.item_type == _EPISODE and row.series_name is not None:
            episodes[(at.date(), row.series_name)].add(row.item_id)
    return sum(len(items) >= _BINGE_MIN_EPISODES for items in episodes.values())


def marathon_days(plays: list[LocalPlay]) -> int:
    return sum(
        _seconds(rows) >= _MARATHON_MIN_SECONDS
        for rows in _rows_by_day(plays).values()
    )


def max_weekend_plays(plays: list[LocalPlay]) -> int:
    """The most plays across one Saturday and the Sunday that follows."""
    weekends: dict[date, int] = defaultdict(int)
    for _, at in plays:
        weekday = at.weekday()
        if weekday in (_SATURDAY, _SUNDAY):
            weekends[at.date() - timedelta(days=weekday - _SATURDAY)] += 1
    return max(weekends.values(), default=0)


def new_year_rows(plays: list[LocalPlay]) -> list[PlaybackSession]:
    """The rows started on December 31 or January 1."""
    return [row for row, at in plays if (at.month, at.day) in _NEW_YEAR_DAYS]


LOCAL_TIME_RULES: dict[str, Callable[[list[LocalPlay]], int]] = {
    "night_watch": night_watch,
    "marathon_hours": marathon_days,
    "weekend_plays": max_weekend_plays,
    "speed_runner": speed_runner,
    "binge_session": binge_session,
    "secret_early_bird": early_bird,
    "secret_newyear": new_year,
    "secret_friday13": friday_13,
    "secret_indecisive": indecisive,
    "secret_summer": summer,
    "secret_ghost": ghost,
    "secret_countdown": countdown,
    "secret_sunday": sunday,
    "secret_butterfly": butterfly,
    "secret_triple": triple,
    "secret_gourmet": gourmet,
}
