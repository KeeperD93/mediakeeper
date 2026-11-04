"""Secret achievement checks — part A (first_play, content-based)."""
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement
from models.playback_stats import PlaybackSession
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.portal.achievements_utils import (
    update_progress,
    _coerce_utc,
)


async def check_secrets_a(
    db: AsyncSession,
    by_type: dict[str, list[Achievement]],
    user_id: int,
    ua_map: dict,
    unlocked_ids: set[str],
    user_filter,
    excl_filters: list,
    playback_rows: list | None,
) -> list[dict]:
    """Run first half of secret checks (first_play..4k). Returns newly unlocked list.

    ``playback_rows`` goes unused here: it comes with the arguments the passes share.
    """
    unlocks: list[dict] = []

    async def _apply(cond_type: str, value: int):
        if cond_type not in by_type:
            return
        for ach in by_type[cond_type]:
            if ach.id in unlocked_ids:
                continue
            r = await update_progress(db, user_id, ach.id, new_value=value, ua_map=ua_map)
            if r:
                unlocks.append(r)

    # --- secret_first_play: 1 if user has any playback session ---
    if "secret_first_play" in by_type:
        val = (await db.execute(
            select(func.count(PlaybackSession.id))
            .where(user_filter, *excl_filters)
            .limit(1)
        )).scalar() or 0
        await _apply("secret_first_play", 1 if val > 0 else 0)

    # --- secret_classic: any session on a title released before 1970 ---
    # Lifetime, threshold = 1; cap to 1 so an ever-growing classics run
    # doesn't push update_progress past the unlock semantics.
    if "secret_classic" in by_type:
        val = (await db.execute(
            select(func.count(PlaybackSession.id))
            .select_from(PlaybackSession)
            .join(
                EmbyTmdbIndex,
                PlaybackSession.item_id == EmbyTmdbIndex.emby_item_id,
            )
            .where(
                user_filter,
                EmbyTmdbIndex.production_year < 1970,
                *excl_filters,
            )
        )).scalar() or 0
        await _apply("secret_classic", min(val, 1))

    # --- secret_nostalgia: rewatched same item 6+ months later ---
    if "secret_nostalgia" in by_type:
        rewatch_rows = (await db.execute(
            select(PlaybackSession.item_id, PlaybackSession.started_at)
            .where(user_filter, *excl_filters)
            .order_by(PlaybackSession.started_at)
        )).all()
        item_first_seen: dict[str, datetime] = {}
        val = 0
        for row in rewatch_rows:
            started = _coerce_utc(row.started_at)
            if not started:
                continue
            if row.item_id in item_first_seen:
                delta = started - item_first_seen[row.item_id]
                if delta.days >= 180:
                    val = 1
                    break
            else:
                item_first_seen[row.item_id] = started
        await _apply("secret_nostalgia", val)

    # --- secret_double: 2 movies ending/starting within 5 min ---
    if "secret_double" in by_type:
        movie_sessions = (await db.execute(
            select(PlaybackSession.started_at, PlaybackSession.ended_at)
            .where(
                user_filter, *excl_filters,
                PlaybackSession.item_type == "Movie",
            )
            .order_by(PlaybackSession.started_at)
        )).all()
        val = 0
        for i in range(len(movie_sessions) - 1):
            ended = _coerce_utc(movie_sessions[i].ended_at)
            next_started = _coerce_utc(movie_sessions[i + 1].started_at)
            if ended and next_started:
                gap = abs((next_started - ended).total_seconds())
                if gap <= 300:
                    val = 1
                    break
        await _apply("secret_double", val)

    # --- secret_4k: count plays with 4K resolution ---
    if "secret_4k" in by_type:
        val = (await db.execute(
            select(func.count(PlaybackSession.id))
            .where(
                user_filter, *excl_filters,
                PlaybackSession.resolution == "4K",
            )
        )).scalar() or 0
        await _apply("secret_4k", val)

    return unlocks
