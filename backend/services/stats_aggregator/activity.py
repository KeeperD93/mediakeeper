"""Paginated activity history + 24h minimap."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.pagination import decode_cursor, build_cursor_response
from models.playback_stats import PlaybackSession

from .exclusions import _get_exclusion_filters
from .playback import _load_mk_profile_map


async def get_activity_history(db: AsyncSession, page: int = 1, per_page: int = 30,
                               search: str = "", cursor: str = "", limit: int = 0):
    """Paginated history of all playbacks (cursor-based or offset fallback)."""
    use_cursor = bool(cursor or limit)
    effective_limit = limit if limit > 0 else per_page

    exc_filters = await _get_exclusion_filters(db)
    query = select(PlaybackSession).order_by(desc(PlaybackSession.id))

    for f in exc_filters:
        query = query.where(f)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                PlaybackSession.user_name.ilike(search_filter),
                PlaybackSession.item_name.ilike(search_filter),
                PlaybackSession.series_name.ilike(search_filter),
                PlaybackSession.client_name.ilike(search_filter),
                PlaybackSession.device_name.ilike(search_filter),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    if use_cursor:
        decoded = decode_cursor(cursor)
        if decoded and "id" in decoded:
            query = query.where(PlaybackSession.id < decoded["id"])
        rows_res = await db.execute(query.limit(effective_limit + 1))
        rows = rows_res.scalars().all()
        has_more = len(rows) > effective_limit
        rows = rows[:effective_limit]
        items = [_activity_row_to_dict(r) for r in rows]
        return build_cursor_response(items, total, effective_limit, cursor_field="id", has_more=has_more)

    offset = (page - 1) * per_page
    rows_res = await db.execute(query.offset(offset).limit(per_page))
    rows = rows_res.scalars().all()

    return {
        "items": [_activity_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def _activity_row_to_dict(r) -> dict:
    return {
        "id": r.id,
        "user": r.user_name,
        "user_id": r.user_id,
        "title": f"{r.series_name} - {r.item_name}" if r.series_name else r.item_name,
        "type": r.item_type,
        "episode": f"S{r.season_number:02d}E{r.episode_number:02d}" if r.season_number is not None and r.episode_number is not None else "",
        "library": r.library_name,
        "client": r.client_name,
        "device": r.device_name,
        "play_method": r.play_method,
        "ip": r.ip_address,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "duration_ticks": r.position_ticks or 0,
    }


async def get_activity_minimap(db: AsyncSession):
    """Return playbacks from the last 24h for the minimap (lightweight fields).

    Each row carries the Emby ``user_id`` plus the MK profile
    ``avatar_url`` + ``tier`` resolved against UserProfile so the
    StatsTotalsRow dedup'ed avatar strip can render real photos +
    tier rings (bronze fallback for Emby-only / historical accounts).
    """
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    exc_filters = await _get_exclusion_filters(db)

    query = (
        select(
            PlaybackSession.started_at,
            PlaybackSession.play_method,
            PlaybackSession.user_name,
            PlaybackSession.user_id,
        )
        .where(PlaybackSession.started_at >= since)
        .order_by(desc(PlaybackSession.started_at))
    )
    for f in exc_filters:
        query = query.where(f)

    result = await db.execute(query)
    rows = result.all()

    mk_profiles = await _load_mk_profile_map(
        db, list({r.user_id for r in rows if r.user_id}),
    )

    return [
        {
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "play_method": r.play_method,
            "user": r.user_name,
            "user_id": r.user_id,
            "avatar_url": (mk_profiles.get(r.user_id) or {}).get("avatar_url"),
            "tier": (mk_profiles.get(r.user_id) or {}).get("tier", "bronze"),
        }
        for r in rows
    ]
