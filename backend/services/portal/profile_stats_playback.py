"""Playback-derived profile stats: totals, streak, records.

Heavy sub-computations live in sibling modules and are re-exported here so
existing callers keep a single import surface:
- ``profile_stats_rewatched`` — most-rewatched movie / series
- ``profile_stats_viewing`` — genres, marathon, media-type ratio
"""
import logging
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime, tzinfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession
from services.instance_time import to_local
from services.portal.play_streak import current_streak, most_played

# Re-exports — keep existing import path `from services.portal.profile_stats_playback import ...`
from services.portal.profile_stats_rewatched import compute_most_rewatched  # noqa: F401
from services.portal.profile_stats_viewing import (  # noqa: F401
    compute_genre_stats,
    compute_longest_session,
    compute_media_type_ratio,
)

logger = logging.getLogger("mediakeeper.portal.profile_stats")

# Time-of-day buckets of the profile card, in display order.
_HOUR_BUCKETS = {
    "morning": range(6, 12),
    "afternoon": range(12, 18),
    "evening": range(18, 23),
    "night": (23, 0, 1, 2, 3, 4, 5),
}
_WEEK = range(7)  # Monday is 0.


async def compute_totals(db: AsyncSession, user_filter, excl_filters: list) -> tuple[int, int]:
    """Return (total_plays, total_minutes)."""
    total_plays = 0
    try:
        result = await db.execute(
            select(func.count(PlaybackSession.id)).where(user_filter, *excl_filters)
        )
        total_plays = result.scalar() or 0
    except Exception as e:
        logger.debug("[PROFILE] total plays error: %s", e)

    # Measured watch time (stats_collector._measure): pauses, seeks and silent
    # players never count, and two devices playing at once count once.
    total_minutes = 0
    try:
        result = await db.execute(
            select(func.coalesce(func.sum(PlaybackSession.exclusive_seconds), 0))
            .where(user_filter, *excl_filters)
        )
        total_minutes = (result.scalar() or 0) // 60
    except Exception as e:
        logger.debug("[PROFILE] total time error: %s", e)

    return total_plays, total_minutes


async def _local_starts(
    db: AsyncSession, user_filter, excl_filters: list, zone: tzinfo,
) -> list[datetime]:
    """When each play started, on the clock of ``zone``: SQL only knows the session's zone."""
    result = await db.execute(
        select(PlaybackSession.started_at).where(user_filter, *excl_filters)
    )
    return [to_local(started, zone) for started in result.scalars() if started]


async def compute_streak(
    db: AsyncSession, user_filter, excl_filters: list, zone: tzinfo,
) -> int:
    """Consecutive days with at least 1 play, on the calendar of ``zone``."""
    try:
        starts = await _local_starts(db, user_filter, excl_filters, zone)
        days = {start.date() for start in starts}
        return current_streak(days, to_local(datetime.now(UTC), zone).date())
    except Exception as e:
        logger.debug("[PROFILE] streak error: %s", e)
    return 0


def _record(keys: Iterable[str], label: str) -> dict:
    """The most frequent of ``keys``, ISO dates, which sort by date."""
    counts = Counter(keys)
    if not counts:
        return {label: None, "count": 0}
    best = most_played(counts)
    return {label: best, "count": counts[best]}


def _calendar_stats(starts: list[datetime]) -> dict:
    days = [start.date().isoformat() for start in starts]
    hours = Counter(start.hour for start in starts)
    weekdays = Counter(start.weekday() for start in starts)
    return {
        "record_day": _record(days, "date"),
        "record_month": _record((day[:7] for day in days), "month"),
        "hour_buckets": [
            {"bucket": bucket, "count": sum(hours[hour] for hour in span)}
            for bucket, span in _HOUR_BUCKETS.items()
        ],
        "day_stats": [{"day": day, "count": weekdays[day]} for day in _WEEK],
    }


async def compute_calendar_stats(
    db: AsyncSession, user_filter, excl_filters: list, zone: tzinfo,
) -> dict:
    """Best day, best month, plays per time of day and per weekday, on the clock of ``zone``.

    One read and one pass for all four. A failed read shows no weekday at all.
    """
    try:
        return _calendar_stats(await _local_starts(db, user_filter, excl_filters, zone))
    except Exception as e:
        logger.error("[PROFILE] calendar stats failed: %s", e)
        return _calendar_stats([]) | {"day_stats": None}
