"""Trophy rules on the local clock: each rule on both sides of its limit, in UTC and in Paris."""
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from models.playback_stats import PlaybackSession
from services.portal.achievements_local_time import (
    LOCAL_TIME_RULES,
    local_plays,
    new_year_rows,
)
from services.portal.play_streak import longest_streak

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


@pytest.mark.parametrize(
    ("condition", "moment", "in_utc", "in_paris"),
    [
        # Paris is UTC+1 in January and UTC+2 in July.
        ("night_watch", _at(2026, 1, 15, 22, 59), 0, 0),  # 23:59
        ("night_watch", _at(2026, 1, 15, 23, 0), 0, 1),  # 00:00
        ("night_watch", _at(2026, 1, 16, 3, 59), 1, 1),  # 04:59
        ("night_watch", _at(2026, 1, 16, 4, 0), 1, 0),  # 05:00
        ("night_watch", _at(2026, 7, 15, 21, 59), 0, 0),  # 23:59
        ("night_watch", _at(2026, 7, 15, 22, 0), 0, 1),  # 00:00
        ("night_watch", _at(2026, 7, 16, 3, 0), 1, 0),  # 05:00
        ("secret_early_bird", _at(2026, 1, 16, 3, 59), 0, 0),  # 04:59
        ("secret_early_bird", _at(2026, 1, 16, 4, 0), 0, 1),  # 05:00
        ("secret_early_bird", _at(2026, 1, 16, 5, 0), 1, 0),  # 06:00
        ("secret_early_bird", _at(2026, 7, 16, 3, 0), 0, 1),  # 05:00
        ("secret_newyear", _at(2025, 12, 31, 22, 59), 0, 0),  # 23:59 on the 31st
        ("secret_newyear", _at(2025, 12, 31, 23, 0), 0, 1),  # 00:00 on the 1st
        ("secret_newyear", _at(2025, 12, 31, 23, 59), 0, 1),  # 00:59 on the 1st
        ("secret_newyear", _at(2026, 1, 1, 0, 0), 1, 0),  # 01:00 on the 1st
        ("secret_ghost", _at(2026, 1, 15, 23, 59), 0, 0),  # 00:59
        ("secret_ghost", _at(2026, 1, 16, 0, 0), 0, 1),  # 01:00
        ("secret_ghost", _at(2026, 1, 16, 2, 59), 1, 1),  # 03:59
        ("secret_ghost", _at(2026, 1, 16, 3, 0), 1, 0),  # 04:00
        ("secret_ghost", _at(2026, 7, 15, 23, 0), 0, 1),  # 01:00
        ("secret_countdown", _at(2026, 1, 15, 22, 58, 59), 0, 0),  # 23:58:59
        ("secret_countdown", _at(2026, 1, 15, 22, 59), 0, 1),  # 23:59:00
        ("secret_countdown", _at(2026, 1, 15, 23, 1, 59), 0, 1),  # 00:01:59
        ("secret_countdown", _at(2026, 1, 15, 23, 2), 0, 0),  # 00:02:00
        ("secret_countdown", _at(2026, 1, 15, 23, 59), 1, 0),  # 00:59
        ("secret_countdown", _at(2026, 7, 15, 21, 59), 0, 1),  # 23:59
    ],
)
def test_rules_on_the_hour_of_a_play(condition, moment, in_utc, in_paris):
    assert _values(condition, [_row(moment)]) == (in_utc, in_paris)


@pytest.mark.parametrize(
    ("moment", "genres", "in_utc", "in_paris"),
    [
        (_at(2026, 2, 12, 23, 30), "Horror", 0, 1),  # Friday the 13th at 00:30
        (_at(2026, 2, 13, 22, 59), "Horreur, Comedy", 1, 1),  # 23:59 the same day
        (_at(2026, 2, 13, 23, 0), " horror ", 1, 0),  # Saturday at 00:00
        (_at(2025, 6, 12, 22, 0), "Horror", 0, 1),  # summer: Friday the 13th at 00:00
        (_at(2026, 2, 13, 12, 0), "Comedy", 0, 0),
        (_at(2026, 2, 13, 12, 0), None, 0, 0),
        (_at(2026, 1, 13, 12, 0), "Horror", 0, 0),  # a Tuesday the 13th
        (_at(2026, 2, 20, 12, 0), "Horror", 0, 0),  # a Friday the 20th
    ],
)
def test_friday_the_13th(moment, genres, in_utc, in_paris):
    assert _values("secret_friday13", [_row(moment, genres=genres)]) == (in_utc, in_paris)


@pytest.mark.parametrize(
    ("moment", "genres", "in_utc", "in_paris"),
    [
        (_at(2026, 6, 30, 21, 59), "Action", 0, 0),  # 23:59 on June 30
        (_at(2026, 6, 30, 22, 0), "Action", 0, 1),  # 00:00 on July 1
        (_at(2026, 8, 31, 21, 59), "Aventure", 1, 1),  # 23:59 on August 31
        (_at(2026, 8, 31, 22, 0), "adventure", 1, 0),  # 00:00 on September 1
        (_at(2026, 7, 15, 12, 0), "Comedy", 0, 0),
        (_at(2026, 7, 15, 12, 0), None, 0, 0),
    ],
)
def test_summer(moment, genres, in_utc, in_paris):
    assert _values("secret_summer", [_row(moment, genres=genres)]) == (in_utc, in_paris)


def test_half_hour_zones_keep_their_minutes():
    kolkata = ZoneInfo("Asia/Kolkata")
    rule = LOCAL_TIME_RULES["secret_countdown"]
    assert rule(local_plays([_row(_at(2026, 1, 15, 18, 29))], kolkata)) == 1  # 23:59
    assert rule(local_plays([_row(_at(2026, 1, 15, 18, 28))], kolkata)) == 0  # 23:58


def test_new_year_rows_are_the_31st_and_the_1st_of_the_local_calendar():
    december_30 = _row(_at(2026, 12, 30, 23, 30))  # the 31st in Paris
    january_1 = _row(_at(2026, 1, 1, 23, 30))  # the 2nd in Paris
    assert new_year_rows(local_plays([december_30], UTC)) == []
    assert new_year_rows(local_plays([december_30], PARIS)) == [december_30]
    assert new_year_rows(local_plays([january_1], UTC)) == [january_1]
    assert new_year_rows(local_plays([january_1], PARIS)) == []


def test_naive_starts_are_utc_and_rows_without_a_start_are_left_out():
    naive = _row(datetime(2026, 1, 15, 23, 30))
    assert _values("night_watch", [naive]) == (0, 1)
    assert local_plays([_row(None)], PARIS) == []


@pytest.mark.parametrize(
    ("zone", "moment"),
    [
        ("America/New_York", datetime(1, 1, 1, tzinfo=UTC)),
        ("Asia/Tokyo", datetime(9999, 12, 31, 23, tzinfo=UTC)),
    ],
)
def test_a_date_at_the_edge_of_the_calendar_breaks_no_rule(zone, moment):
    plays = local_plays([_row(moment)], ZoneInfo(zone))
    assert plays[0].at == moment
    for rule in LOCAL_TIME_RULES.values():
        rule(plays)


def test_a_night_session_no_longer_breaks_a_streak():
    """22:22 UTC is 00:22 the next day in Paris: without it, a day looks empty."""
    rows = [_row(_at(2026, 10, 14, 22, 22)), _row(_at(2026, 10, 16, 16, 49))]
    utc_days = {play.at.date() for play in local_plays(rows, UTC)}
    paris_days = {play.at.date() for play in local_plays(rows, PARIS)}
    assert longest_streak(utc_days) == 1
    assert longest_streak(paris_days) == 2
