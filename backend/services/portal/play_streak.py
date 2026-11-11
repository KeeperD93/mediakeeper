"""Runs of consecutive days with at least one play, and the busiest moment."""
from collections.abc import Iterable, Mapping
from datetime import date, timedelta

_ONE_DAY = timedelta(days=1)


def most_played[K](counts: Mapping[K, int]) -> K:
    """The key with the most plays. The earliest stays on a tie: equalling is not beating."""
    return min(counts, key=lambda key: (-counts[key], key))


def current_streak(days: Iterable[date], today: date) -> int:
    """Days in a row up to ``today``, or up to yesterday while today can still extend them."""
    played = set(days)
    day = today if today in played else today - _ONE_DAY
    run = 0
    while day in played:
        run += 1
        day -= _ONE_DAY
    return run


def longest_streak(days: Iterable[date]) -> int:
    """The longest run of days in a row, whenever it happened."""
    longest = run = 0
    previous = None
    for day in sorted(set(days)):
        run = run + 1 if previous is not None and day - previous == _ONE_DAY else 1
        longest = max(longest, run)
        previous = day
    return longest
