"""Playback-derived profile stats: totals, streak, records.

Heavy sub-computations live in sibling modules and are re-exported here so
existing callers keep a single import surface:
- ``profile_stats_rewatched`` — most-rewatched movie / series
- ``profile_stats_viewing`` — genres, marathon, media-type ratio, hour/day buckets
"""
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession

# Re-exports — keep existing import path `from services.portal.profile_stats_playback import ...`
from services.portal.profile_stats_rewatched import compute_most_rewatched  # noqa: F401
from services.portal.profile_stats_viewing import (  # noqa: F401
    compute_genre_stats,
    compute_longest_session,
    compute_media_type_ratio,
    compute_hour_buckets,
    compute_day_stats,
)

logger = logging.getLogger("mediakeeper.portal.profile_stats")


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

    # Total watch time (minutes), from started_at → ended_at (fallback last_seen_at),
    # with duration_ticks as a last-resort fallback.
    total_minutes = 0
    try:
        result = await db.execute(
            select(
                PlaybackSession.started_at,
                PlaybackSession.ended_at,
                PlaybackSession.last_seen_at,
                PlaybackSession.duration_ticks,
            ).where(user_filter, *excl_filters)
        )
        total_secs = 0
        for row in result.all():
            if row.started_at:
                ended = row.ended_at or row.last_seen_at
                if ended and ended >= row.started_at:
                    total_secs += int((ended - row.started_at).total_seconds())
                    continue
            if row.duration_ticks:
                total_secs += int(row.duration_ticks / 10_000_000)
        total_minutes = total_secs // 60
    except Exception as e:
        logger.debug("[PROFILE] total time error: %s", e)

    return total_plays, total_minutes


async def compute_streak(db: AsyncSession, user_filter, excl_filters: list) -> int:
    """Consecutive days with at least 1 play. Shared with achievements."""
    try:
        result = await db.execute(
            select(func.date(PlaybackSession.started_at))
            .where(user_filter, *excl_filters)
            .group_by(func.date(PlaybackSession.started_at))
            .order_by(desc(func.date(PlaybackSession.started_at)))
        )
        dates = [r[0] for r in result.all()]
        if dates:
            today = datetime.now(timezone.utc).date()
            if dates[0] == today or dates[0] == today - timedelta(days=1):
                streak = 1
                for i in range(1, len(dates)):
                    if dates[i] == dates[i - 1] - timedelta(days=1):
                        streak += 1
                    else:
                        break
                return streak
    except Exception as e:
        logger.debug("[PROFILE] streak error: %s", e)
    return 0


async def compute_record_day(db: AsyncSession, user_filter, excl_filters: list) -> dict:
    """Day with the most plays."""
    record_day = {"date": None, "count": 0}
    try:
        result = await db.execute(
            select(
                func.date(PlaybackSession.started_at).label("day"),
                func.count(PlaybackSession.id).label("cnt"),
            )
            .where(user_filter, *excl_filters)
            .group_by("day")
            .order_by(desc("cnt"))
            .limit(1)
        )
        row = result.first()
        if row:
            record_day = {"date": str(row.day), "count": row.cnt}
    except Exception as e:
        logger.debug("[PROFILE] record error: %s", e)
    return record_day


async def compute_record_month(
    db: AsyncSession, user_filter, excl_filters: list,
) -> dict:
    """Calendar month with the most plays. Returns {month: "YYYY-MM", count: N}."""
    record = {"month": None, "count": 0}
    try:
        result = await db.execute(
            select(
                func.to_char(PlaybackSession.started_at, "YYYY-MM").label("ym"),
                func.count(PlaybackSession.id).label("cnt"),
            )
            .where(user_filter, *excl_filters)
            .group_by("ym")
            .order_by(desc("cnt"))
            .limit(1)
        )
        row = result.first()
        if row and row.ym:
            record = {"month": row.ym, "count": row.cnt}
    except Exception as e:
        logger.debug("[PROFILE] record month error: %s", e)
    return record
