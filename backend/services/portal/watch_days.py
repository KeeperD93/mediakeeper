"""The days something was watched on, on the clock of the instance: what a day streak counts.

A day counts once it holds five minutes of watching, whatever day the titles started on: a
film finished after midnight fills the new day too. Only measured time counts, so pauses
and a title stopped at once fill nothing; music and audiobooks never count.
"""
from collections import Counter
from collections.abc import Iterable
from datetime import date, tzinfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.playback import AUDIO_ITEM_TYPES, WATCH_ITEM_TYPES
from models.playback_stats import PlaybackSession
from services.instance_time import to_local
from services.watch_hours import hour_start, spread_over_hours

MIN_WATCHED_SECONDS_PER_DAY = 5 * 60

# What ``watch_days`` reads of each play.
_COLUMNS = (
    PlaybackSession.item_type,
    PlaybackSession.started_at,
    PlaybackSession.watched_seconds,
    PlaybackSession.watched_by_hour,
)


def _watched_by_hour(play) -> dict[str, int] | None:
    """Films and episodes keep their time per hour; other video only per title, laid from its start."""
    if play.item_type in AUDIO_ITEM_TYPES:
        return None
    if play.item_type in WATCH_ITEM_TYPES:
        return play.watched_by_hour
    if play.started_at is None:
        return None
    return spread_over_hours(play.started_at, play.watched_seconds)


def watch_days(plays: Iterable, zone: tzinfo) -> set[date]:
    """The days of ``zone`` holding enough watching, summed over ``plays`` (rows of ``_COLUMNS``).

    An hour goes to the day it starts in: in a zone off by half an hour, the half
    past midnight stays with the day before.
    """
    per_hour: Counter[str] = Counter()
    for play in plays:
        per_hour.update(_watched_by_hour(play) or {})
    per_day: Counter[date] = Counter()
    for hour, seconds in per_hour.items():
        per_day[to_local(hour_start(hour), zone).date()] += seconds
    return {day for day, seconds in per_day.items() if seconds >= MIN_WATCHED_SECONDS_PER_DAY}


async def load_watch_days(db: AsyncSession, filters: Iterable, zone: tzinfo) -> set[date]:
    """``watch_days`` of the plays matching ``filters``."""
    result = await db.execute(select(*_COLUMNS).where(*filters))
    return watch_days(result.all(), zone)
