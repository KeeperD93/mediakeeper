"""The days something was watched on, on the clock of the instance: what a day streak counts.

A day counts once it holds five minutes of watching, whatever day the titles started on: a
film finished after midnight fills the new day too. Films and episodes bring their seconds
per hour (estimated for imported history), other video its time per title laid from its
start, two of one account at once counting once. Pauses and a title stopped at once fill
nothing; music and audiobooks never count.
"""
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from datetime import UTC, date, datetime, timedelta, tzinfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.playback import AUDIO_ITEM_TYPES, WATCH_ITEM_TYPES
from models.playback_stats import PlaybackSession
from services.instance_time import to_local
from services.watch_hours import hour_start, spread_over_hours

MIN_WATCHED_SECONDS_PER_DAY = 5 * 60
_LAST_INSTANT_OF_AN_HOUR = timedelta(hours=1, microseconds=-1)
_SECOND = timedelta(seconds=1)

# What ``watch_days`` reads of each play.
WATCH_DAY_COLUMNS = (
    PlaybackSession.user_id,
    PlaybackSession.item_type,
    PlaybackSession.started_at,
    PlaybackSession.watched_seconds,
    PlaybackSession.watched_by_hour,
)


def _merged(spans: list[tuple[datetime, datetime]]) -> Iterator[tuple[datetime, datetime]]:
    """``spans`` in order, each run of overlapping ones as a single span."""
    spans.sort()
    start, end = spans[0]
    for next_start, next_end in spans[1:]:
        if next_start < end:
            end = max(end, next_end)
        else:
            yield start, end
            start, end = next_start, next_end
    yield start, end


def _seconds_per_hour(plays: Iterable) -> Counter[str]:
    """Films and episodes keep their time per hour; other video only per title, laid from its
    start, where the plays of one account that overlap count once (never across accounts)."""
    per_hour: Counter[str] = Counter()
    spans: defaultdict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    for play in plays:
        if play.item_type in AUDIO_ITEM_TYPES:
            continue
        if play.item_type in WATCH_ITEM_TYPES:
            per_hour.update(play.watched_by_hour or {})
        elif play.started_at is not None:
            # SQLite leaves the moment naive: made aware, it sorts with the others.
            start = to_local(play.started_at, UTC)
            spans[play.user_id].append((start, start + timedelta(seconds=play.watched_seconds)))
    for account in spans.values():
        for start, end in _merged(account):
            per_hour.update(spread_over_hours(start, (end - start) // _SECOND))
    return per_hour


def watch_days(plays: Iterable, zone: tzinfo, *, generous: bool = False) -> set[date]:
    """The days of ``zone`` holding enough watching, summed over ``plays`` (``WATCH_DAY_COLUMNS``).

    An hour goes to the day it starts in: in a zone off by half an hour, the half
    past midnight stays with the day before. ``generous`` gives such an hour to both
    days, for a judge that must never take a day away.
    """
    per_day: Counter[date] = Counter()
    for hour, seconds in _seconds_per_hour(plays).items():
        start = hour_start(hour)
        first = to_local(start, zone).date()
        per_day[first] += seconds
        if generous:
            last = to_local(start + _LAST_INSTANT_OF_AN_HOUR, zone).date()
            if last != first:
                per_day[last] += seconds
    return {day for day, seconds in per_day.items() if seconds >= MIN_WATCHED_SECONDS_PER_DAY}


async def load_watch_days(db: AsyncSession, filters: Iterable, zone: tzinfo) -> set[date]:
    """``watch_days`` of the plays matching ``filters``."""
    result = await db.execute(select(*WATCH_DAY_COLUMNS).where(*filters))
    return watch_days(result.all(), zone)
