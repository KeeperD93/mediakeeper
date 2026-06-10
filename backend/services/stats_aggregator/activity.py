"""Paginated activity history + 24h minimap."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, desc, or_, nulls_last
from sqlalchemy.ext.asyncio import AsyncSession

from core.pagination import build_cursor_response, decode_cursor, encode_cursor
from models.playback_stats import PlaybackSession

from .exclusions import _get_exclusion_filters
from .playback import _load_mk_profile_map, _resolve_user_avatar


async def _activity_base_query(db: AsyncSession, search: str, exclude_users: str):
    """Filtered (exclusions + user filter + search) PlaybackSession select, unordered."""
    query = select(PlaybackSession)
    for f in await _get_exclusion_filters(db):
        query = query.where(f)

    excluded_ids = [u for u in exclude_users.split(",") if u]
    if excluded_ids:
        query = query.where(PlaybackSession.user_id.notin_(excluded_ids))

    if search:
        sf = f"%{search}%"
        query = query.where(
            or_(
                PlaybackSession.user_name.ilike(sf),
                PlaybackSession.item_name.ilike(sf),
                PlaybackSession.series_name.ilike(sf),
                PlaybackSession.client_name.ilike(sf),
                PlaybackSession.device_name.ilike(sf),
            )
        )
    return query


# Columns the flat (ungrouped) list sorts on server-side. "Durée" is absent on
# purpose: it is derived (last_seen - started, capped at the runtime), not a
# stored column, so it can't be ordered portably across SQLite/Postgres.
_SORT_COLUMNS = {
    "user": PlaybackSession.user_name,
    "title": func.coalesce(PlaybackSession.series_name, PlaybackSession.item_name),
    "client": PlaybackSession.client_name,
    "play_method": PlaybackSession.play_method,
    "started_at": PlaybackSession.started_at,
}


def _activity_order(sort_by: str, sort_order: str):
    """ORDER BY for the flat list; ``id`` breaks ties so paging stays stable.

    ``nulls_last`` keeps the nullable columns (client_name, play_method) ordered
    the same way on SQLite and Postgres, whose default NULL placement differs.
    """
    col = _SORT_COLUMNS.get(sort_by, PlaybackSession.started_at)
    primary = col.asc() if sort_order == "asc" else col.desc()
    return nulls_last(primary), desc(PlaybackSession.id)


async def get_activity_history(db: AsyncSession, page: int = 1, per_page: int = 30,
                               search: str = "", cursor: str = "", limit: int = 0,
                               exclude_users: str = "", sort_by: str = "started_at",
                               sort_order: str = "desc"):
    """Paginated flat history of all playbacks (cursor-based or offset fallback).

    ``exclude_users`` is a comma-separated list of Emby user ids whose rows are
    hidden from the result — an ephemeral display filter, not a stored setting.
    ``sort_by``/``sort_order`` only apply to the offset branch (the sorted views);
    cursor paging stays id-based (recent-first).
    """
    use_cursor = bool(cursor or limit)
    effective_limit = limit if limit > 0 else per_page

    base = await _activity_base_query(db, search, exclude_users)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    if use_cursor:
        query = base.order_by(desc(PlaybackSession.id))
        decoded = decode_cursor(cursor)
        if decoded and "id" in decoded:
            query = query.where(PlaybackSession.id < decoded["id"])
        rows = (await db.execute(query.limit(effective_limit + 1))).scalars().all()
        has_more = len(rows) > effective_limit
        rows = rows[:effective_limit]
        items = [_activity_row_to_dict(r) for r in rows]
        return build_cursor_response(items, total, effective_limit, cursor_field="id", has_more=has_more)

    query = base.order_by(*_activity_order(sort_by, sort_order))
    offset = (page - 1) * per_page
    rows = (await db.execute(query.offset(offset).limit(per_page))).scalars().all()
    return {
        "items": [_activity_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# Max rows scanned per grouped page. Bounds the (pathological) case of a single
# film watched in hundreds of back-to-back sessions; well above any real run.
_GROUP_SCAN_CAP = 800


def _group_to_dict(run: list) -> dict:
    """Turn a run of consecutive same-(user, item) sessions into one parent row.

    The representative is the latest session (run is ordered id desc); the full
    session list is attached for the expander + the segmented progress bar.
    """
    sessions = [_activity_row_to_dict(r) for r in run]
    parent = dict(sessions[0])  # latest session
    parent["session_count"] = len(run)
    parent["max_position_ticks"] = max((s["position_ticks"] for s in sessions), default=0)
    parent["sessions"] = sessions
    return parent


async def get_activity_grouped(db: AsyncSession, limit: int = 25, cursor: str = "",
                               search: str = "", exclude_users: str = "") -> dict:
    """Chronological activity with consecutive same-(user, item) sessions merged.

    Groups never split across pages: we return only complete runs and stop at the
    last one whose boundary is confirmed within the scan window.
    """
    base = await _activity_base_query(db, search, exclude_users)
    query = base.order_by(desc(PlaybackSession.id))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    decoded = decode_cursor(cursor)
    if decoded and "id" in decoded:
        query = query.where(PlaybackSession.id < decoded["id"])

    rows = (await db.execute(query.limit(_GROUP_SCAN_CAP + 1))).scalars().all()
    hit_cap = len(rows) > _GROUP_SCAN_CAP
    rows = rows[:_GROUP_SCAN_CAP]

    runs: list[list] = []
    for r in rows:
        if runs and runs[-1][0].user_id == r.user_id and runs[-1][0].item_id == r.item_id:
            runs[-1].append(r)
        else:
            runs.append([r])

    if len(runs) > limit:
        page_runs, has_more = runs[:limit], True
    elif hit_cap:
        # Scan window full: the last run may continue past it, so drop it (re-fetched
        # whole next page). If it is the ONLY run, keep it and let the cursor advance
        # through it — a single giant run paginates instead of stalling on dead data.
        page_runs, has_more = (runs[:-1] if len(runs) > 1 else runs), True
    else:
        page_runs, has_more = runs, False

    items = [_group_to_dict(run) for run in page_runs]
    next_cursor = None
    if has_more and page_runs:
        next_cursor = encode_cursor({"id": min(r.id for r in page_runs[-1])})

    return {"items": items, "total": total, "limit": limit,
            "next_cursor": next_cursor, "has_more": has_more}


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


async def get_activity_users(db: AsyncSession) -> list[dict]:
    """Distinct users that appear in the activity history (for the display filter)."""
    rows = (
        await db.execute(
            select(PlaybackSession.user_id, func.max(PlaybackSession.user_name).label("name"))
            .group_by(PlaybackSession.user_id)
            .order_by(func.max(PlaybackSession.user_name))
        )
    ).all()
    return [{"id": uid, "name": name} for uid, name in rows]


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
