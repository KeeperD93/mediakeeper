"""Paginated activity history + 24h minimap."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.pagination import decode_cursor, build_cursor_response
from models.playback_stats import PlaybackSession

from .exclusions import _get_exclusion_filters
from .playback import _load_mk_profile_map, _resolve_user_avatar


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


def _session_ticks(r) -> int:
    """How long a session lasted, in Emby ticks, capped at the media runtime.

    The DB has no dedicated watch-time field; ``last_seen_at - started_at`` is
    the active span. Capping at the runtime neutralises never-closed / live
    sessions whose span can otherwise reach days.
    """
    if not r.started_at or not r.last_seen_at:
        return 0
    span = (r.last_seen_at - r.started_at).total_seconds()
    if span <= 0:
        return 0
    span_ticks = int(span * 1e7)
    runtime = r.duration_ticks or 0
    return min(span_ticks, runtime) if runtime > 0 else span_ticks


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
        # position_ticks = how far into the media this session reached;
        # runtime_ticks = the media total length (both feed the progress column);
        # session_ticks = how long the session lasted (capped at the runtime).
        "position_ticks": r.position_ticks or 0,
        "runtime_ticks": r.duration_ticks or 0,
        "session_ticks": _session_ticks(r),
    }


async def get_activity_minimap(db: AsyncSession):
    """Return playbacks from the last 24h for the minimap (lightweight fields).

    Each row carries the Emby ``user_id`` plus the MK profile
    ``avatar_url`` + ``tier`` resolved against UserProfile so the
    StatsTotalsRow dedup'ed avatar strip can render real photos +
    tier rings. Emby-only / historical accounts (no MK profile row)
    fall back to the Emby-proxied photo URL + bronze tier via
    ``_resolve_user_avatar`` so the strip stays consistent with the
    leaderboard style instead of degrading to silhouettes.
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

    enriched = []
    for r in rows:
        user_meta = _resolve_user_avatar(r.user_id, mk_profiles)
        enriched.append({
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "play_method": r.play_method,
            "user": r.user_name,
            "user_id": r.user_id,
            "avatar_url": user_meta["avatar_url"],
            "tier": user_meta["tier"],
        })
    return enriched
