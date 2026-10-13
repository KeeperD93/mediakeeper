"""Titles counted as watched, recorded the moment they qualify."""
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.playback import WATCH_ITEM_TYPES
from models.playback_stats import PlaybackCompletion, PlaybackSession
from services.portal._watch_threshold import WATCHED_THRESHOLD

from ._measure import TICKS_PER_SECOND, as_utc

# Share of the runtime that must have been really watched (one or several
# sittings); the end itself must be reached (``WATCHED_THRESHOLD``).
WATCHED_TIME_RATIO = 0.75
# Sittings older than this no longer add up to the same viewing.
COMPLETION_WINDOW = timedelta(days=30)


async def _watched_before(db: AsyncSession, row: PlaybackSession, now: datetime) -> int:
    """Seconds watched on the same title in the other sittings that still count."""
    since = now - COMPLETION_WINDOW
    last_done = as_utc(await db.scalar(
        select(func.max(PlaybackCompletion.completed_at)).where(
            PlaybackCompletion.user_id == row.user_id,
            PlaybackCompletion.item_id == row.item_id,
        )
    ))
    if last_done is not None and last_done > since:
        since = last_done
    return await db.scalar(
        select(func.coalesce(func.sum(PlaybackSession.watched_seconds), 0)).where(
            PlaybackSession.user_id == row.user_id,
            PlaybackSession.item_id == row.item_id,
            PlaybackSession.id != row.id,
            PlaybackSession.started_at >= since,
        )
    ) or 0


async def record_completions(db: AsyncSession, rows: list[PlaybackSession], now: datetime) -> int:
    """Record a completion for each row whose title has just qualified as watched.

    Rows must be flushed (``id`` set). A row completes at most once.
    """
    recorded = 0
    for row in rows:
        if row.completed_at is not None or row.item_type not in WATCH_ITEM_TYPES:
            continue
        runtime = (row.duration_ticks or 0) / TICKS_PER_SECOND
        position = (row.position_ticks or 0) / TICKS_PER_SECOND
        if runtime <= 0 or position < runtime * WATCHED_THRESHOLD:
            continue
        total = (row.watched_seconds or 0) + await _watched_before(db, row, now)
        if total < runtime * WATCHED_TIME_RATIO:
            continue
        row.completed_at = now
        db.add(PlaybackCompletion(
            session_id=row.id,
            user_id=row.user_id,
            user_name=row.user_name,
            item_id=row.item_id,
            item_type=row.item_type,
            item_name=row.item_name,
            series_name=row.series_name,
            season_number=row.season_number,
            episode_number=row.episode_number,
            library_name=row.library_name,
            runtime_seconds=int(runtime),
            watched_seconds=int(total),
            completed_at=now,
            source="live",
        ))
        recorded += 1
    return recorded
