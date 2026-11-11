"""Trophy rules on a local day: each rule on both sides of midnight, in UTC and in Paris."""
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from models.playback_stats import PlaybackSession
from services.portal.achievements_local_time import LOCAL_TIME_RULES, local_plays

PARIS = ZoneInfo("Europe/Paris")


def _at(*parts: int) -> datetime:
    return datetime(*parts, tzinfo=UTC)


def _row(moment: datetime | None, **fields) -> PlaybackSession:
    defaults = {
        "item_id": "item-1",
        "item_type": "Movie",
        "measured": True,
        "exclusive_seconds": 60,
    }
    return PlaybackSession(started_at=moment, **{**defaults, **fields})


def _rows(moments: list[datetime], **fields) -> list[PlaybackSession]:
    """One row per moment, each on a title of its own."""
    return [_row(moment, item_id=f"item-{n}", **fields) for n, moment in enumerate(moments)]


def _values(condition: str, rows: list[PlaybackSession]) -> tuple[int, int]:
    """The value of a rule in UTC, then in Paris."""
    rule = LOCAL_TIME_RULES[condition]
    return rule(local_plays(rows, UTC)), rule(local_plays(rows, PARIS))


# One local day in Paris, two in UTC: on each side of midnight UTC.
_ACROSS_UTC_MIDNIGHT = [_at(2026, 1, 15, 23, 10), _at(2026, 1, 16, 0, 10)]
# One day in UTC, two in Paris: on each side of midnight in Paris.
_ACROSS_PARIS_MIDNIGHT = [_at(2026, 1, 15, 22, 10), _at(2026, 1, 15, 23, 10)]


def _split(moments: list[datetime], before: int, after: int) -> list[datetime]:
    return [moments[0]] * before + [moments[1]] * after


@pytest.mark.parametrize(
    ("condition", "count", "fields"),
    [
        ("secret_indecisive", 10, {}),
        ("secret_triple", 3, {}),
        ("speed_runner", 5, {}),
        ("binge_session", 10, {"item_type": "Episode", "series_name": "Test Show"}),
    ],
)
def test_rules_counting_titles_in_a_day(condition, count, fields):
    half = count // 2
    rest = count - half
    together = _rows(_split(_ACROSS_UTC_MIDNIGHT, half, rest), **fields)
    assert _values(condition, together) == (0, 1)
    apart = _rows(_split(_ACROSS_PARIS_MIDNIGHT, half, rest), **fields)
    assert _values(condition, apart) == (1, 0)
    one_short = _rows(_split(_ACROSS_UTC_MIDNIGHT, half, rest - 1), **fields)
    assert _values(condition, one_short) == (0, 0)


@pytest.mark.parametrize(
    ("condition", "fields"),
    [
        ("secret_triple", {}),
        ("speed_runner", {}),
        ("secret_indecisive", {}),
        ("binge_session", {"item_type": "Episode", "series_name": "Test Show"}),
    ],
)
def test_the_same_title_again_counts_once(condition, fields):
    rows = [_row(_at(2026, 1, 15, 12, minute), **fields) for minute in range(12)]
    assert _values(condition, rows) == (0, 0)


def test_rules_with_tiers_count_every_play_and_every_day():
    assert _values("night_watch", _rows([_at(2026, 1, 15, 23, minute) for minute in range(3)])) == (0, 3)
    two_days = [_at(2026, 1, 15 + day, 12, minute) for day in range(2) for minute in range(10)]
    assert _values("speed_runner", _rows(two_days)) == (2, 2)
    episodes = _rows(two_days, item_type="Episode", series_name="Test Show")
    assert _values("binge_session", episodes) == (2, 2)


@pytest.mark.parametrize("condition", ["secret_triple", "speed_runner"])
def test_episodes_are_not_movies(condition):
    rows = _rows([_at(2026, 1, 15, 12, minute) for minute in range(5)], item_type="Episode")
    assert _values(condition, rows) == (0, 0)


def test_binge_needs_one_named_series():
    moments = [_at(2026, 1, 15, 12, minute) for minute in range(10)]
    assert _values("binge_session", _rows(moments, item_type="Episode")) == (0, 0)
    assert _values("binge_session", _rows(moments, series_name="Test Show")) == (0, 0)
    split = [
        _row(moment, item_id=f"item-{n}", item_type="Episode", series_name=f"Show {n % 2}")
        for n, moment in enumerate(moments)
    ]
    assert _values("binge_session", split) == (0, 0)


def test_indecisive_refuses_a_long_session():
    rows = _rows([_at(2026, 1, 15, 12, minute) for minute in range(10)])
    rows[0].exclusive_seconds = 30 * 60
    assert _values("secret_indecisive", rows) == (0, 0)
    rows[0].exclusive_seconds = 30 * 60 - 1
    assert _values("secret_indecisive", rows) == (1, 1)


def test_butterfly_counts_the_genres_of_a_day():
    names = ["Action", "Comedy", "Drama", "Horror", "Romance"]
    moments = _split(_ACROSS_UTC_MIDNIGHT, 2, 3)
    rows = [_row(moment, genres=name) for moment, name in zip(moments, names)]
    assert _values("secret_butterfly", rows) == (0, 1)
    moments = _split(_ACROSS_PARIS_MIDNIGHT, 2, 3)
    rows = [_row(moment, genres=name) for moment, name in zip(moments, names)]
    assert _values("secret_butterfly", rows) == (1, 0)
    four = [_row(_at(2026, 1, 15, 12), genres=", ".join(names[:4]))]
    assert _values("secret_butterfly", four) == (0, 0)
    assert _values("secret_butterfly", four + [_row(_at(2026, 1, 15, 13), genres="Romance")]) == (1, 1)
    # Spelled differently, a genre is another one.
    cased = [_row(_at(2026, 1, 15, 12), genres="Action, action, ACTION, Drama, Comedy")]
    assert _values("secret_butterfly", cased) == (1, 1)
    assert _values("secret_butterfly", [_row(_at(2026, 1, 15, 12), genres=" , ,Action")]) == (0, 0)


def test_sunday_adds_up_the_seconds_of_a_local_sunday():
    six_hours = 6 * 3600
    # Saturday 23:30 UTC is Sunday 00:30 in Paris, Sunday 23:30 UTC is Monday.
    assert _values("secret_sunday", [_row(_at(2026, 1, 17, 23, 30), exclusive_seconds=six_hours)]) == (0, 1)
    assert _values("secret_sunday", [_row(_at(2026, 1, 18, 23, 30), exclusive_seconds=six_hours)]) == (1, 0)
    assert _values("secret_sunday", [_row(_at(2026, 7, 18, 22, 0), exclusive_seconds=six_hours)]) == (0, 1)
    too_short = [_row(_at(2026, 1, 18, 12), exclusive_seconds=six_hours - 1)]
    assert _values("secret_sunday", too_short) == (0, 0)
    two_parts = [
        _row(_at(2026, 1, 18, 12), exclusive_seconds=six_hours - 1),
        _row(_at(2026, 1, 18, 20), exclusive_seconds=1),
    ]
    assert _values("secret_sunday", two_parts) == (1, 1)
    two_sundays = [
        _row(_at(2026, 1, 18, 12), exclusive_seconds=six_hours - 1),
        _row(_at(2026, 1, 25, 12), exclusive_seconds=six_hours - 1),
    ]
    assert _values("secret_sunday", two_sundays) == (0, 0)


def test_marathon_counts_the_days_of_eight_hours():
    four_hours = 4 * 3600
    together = [_row(moment, exclusive_seconds=four_hours) for moment in _ACROSS_UTC_MIDNIGHT]
    assert _values("marathon_hours", together) == (0, 1)
    apart = [_row(moment, exclusive_seconds=four_hours) for moment in _ACROSS_PARIS_MIDNIGHT]
    assert _values("marathon_hours", apart) == (1, 0)
    next_week = [_row(moment + timedelta(days=7), exclusive_seconds=four_hours) for moment in _ACROSS_UTC_MIDNIGHT]
    assert _values("marathon_hours", together + next_week) == (0, 2)


def test_weekend_counts_saturday_and_sunday_on_the_local_clock():
    # Friday 23:30 UTC is Saturday in Paris, Sunday 23:30 UTC is Monday.
    friday_night = _row(_at(2026, 1, 16, 23, 30))
    sunday_night = _row(_at(2026, 1, 18, 23, 30))
    saturday = _row(_at(2026, 1, 17, 12))
    sunday = _row(_at(2026, 1, 18, 12))
    assert _values("weekend_plays", [friday_night]) == (0, 1)
    assert _values("weekend_plays", [sunday_night]) == (1, 0)
    assert _values("weekend_plays", [saturday, sunday]) == (2, 2)
    assert _values("weekend_plays", [friday_night, saturday, sunday, sunday_night]) == (3, 3)
    next_weekend = _row(_at(2026, 1, 24, 12))
    assert _values("weekend_plays", [saturday, next_weekend]) == (1, 1)
    assert _values("weekend_plays", []) == (0, 0)


def test_gourmet_needs_seven_noons_in_a_row():
    # 11:30 UTC is 12:30 in Paris in January.
    noons = [_at(2026, 1, 10 + day, 11, 30) for day in range(7)]
    assert _values("secret_gourmet", _rows(noons)) == (0, 7)
    assert _values("secret_gourmet", _rows(noons[:6])) == (0, 0)
    assert _values("secret_gourmet", _rows(noons[:3] + noons[4:])) == (0, 0)
    # 10:30 UTC is 12:30 in July, 11:00 UTC is 13:00.
    july = [_at(2026, 7, 10 + day, 10, 30) for day in range(7)]
    assert _values("secret_gourmet", _rows(july)) == (0, 7)
    assert _values("secret_gourmet", _rows([_at(2026, 7, 10 + day, 11) for day in range(7)])) == (0, 0)
    assert _values("secret_gourmet", _rows([_at(2026, 1, 10 + day, 12) for day in range(7)])) == (7, 0)


def test_the_days_the_clocks_change_are_one_day_on_the_calendar():
    # March 29 has 23 hours in Paris, October 25 has 25.
    short_day = [_at(2026, 3, 28, 23), _at(2026, 3, 29, 12), _at(2026, 3, 29, 21, 59)]
    assert _values("secret_triple", _rows(short_day)) == (0, 1)
    next_day = [_at(2026, 3, 28, 23), _at(2026, 3, 29, 12), _at(2026, 3, 29, 22)]
    assert _values("secret_triple", _rows(next_day)) == (0, 0)
    long_day = [_at(2026, 10, 24, 22), _at(2026, 10, 25, 12), _at(2026, 10, 25, 22, 59)]
    assert _values("secret_triple", _rows(long_day)) == (0, 1)
    next_day = [_at(2026, 10, 24, 22), _at(2026, 10, 25, 12), _at(2026, 10, 25, 23)]
    assert _values("secret_triple", _rows(next_day)) == (0, 0)
    # 02:30 happens twice in October, and not at all in March.
    assert _values("secret_ghost", [_row(_at(2026, 10, 25, 0, 30))]) == (0, 1)
    assert _values("secret_ghost", [_row(_at(2026, 10, 25, 1, 30))]) == (1, 1)
    assert _values("secret_ghost", [_row(_at(2026, 3, 29, 0, 59))]) == (0, 1)
    assert _values("secret_ghost", [_row(_at(2026, 3, 29, 1, 0))]) == (1, 1)
