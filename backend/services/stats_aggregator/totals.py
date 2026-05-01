"""Global totals (no time window)."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from services.settings import get_active_media_source
from models.playback_stats import PlaybackSession, LibraryCache

from .exclusions import _get_exclusion_filters


async def get_global_totals(db: AsyncSession):
    """Totaux from la mise en place de Mediakeeper — no filtre date."""
    exc_filters = await _get_exclusion_filters(db)

    base_q = select(func.count(PlaybackSession.id))
    dur_q = select(func.sum(PlaybackSession.position_ticks))
    usr_q = select(func.count(distinct(PlaybackSession.user_id))).where(
        PlaybackSession.started_at >= datetime.now(timezone.utc) - timedelta(hours=24)
    )
    meth_q = select(
        PlaybackSession.play_method,
        func.count(PlaybackSession.id).label("count"),
    ).group_by(PlaybackSession.play_method)

    for f in exc_filters:
        base_q = base_q.where(f)
        dur_q = dur_q.where(f)
        usr_q = usr_q.where(f)
        meth_q = meth_q.where(f)

    total_plays_res = await db.execute(base_q)
    total_duration_res = await db.execute(dur_q)
    active_users_24h_res = await db.execute(usr_q)
    by_method_q = await db.execute(meth_q)
    by_method = {r[0] or "Unknown": r[1] for r in by_method_q.all()}

    total_plays = total_plays_res.scalar() or 0
    total_duration_ticks = total_duration_res.scalar() or 0
    active_users_24h = active_users_24h_res.scalar() or 0
    transcode_count = by_method.get("Transcode", 0)
    transcode_pct = round((transcode_count / total_plays * 100), 1) if total_plays > 0 else 0

    storage_res = await db.execute(
        select(func.sum(LibraryCache.size_bytes))
    )
    total_storage_bytes = storage_res.scalar() or 0

    total_users = 0
    disabled_users = 0
    try:
        source = await get_active_media_source(db)
        if source and source.get("source") in ("emby", "jellyfin"):
            url = source.get("url", "").rstrip("/")
            api_key = source.get("api_key", "")
            if url and api_key:
                client = get_internal_client()
                res = await client.get(f"{url}/Users", headers={"X-Emby-Token": api_key}, timeout=10.0)
                if res.status_code == 200:
                    emby_users = res.json()
                    total_users = sum(1 for u in emby_users if not u.get("Policy", {}).get("IsDisabled", False))
                    disabled_users = sum(1 for u in emby_users if u.get("Policy", {}).get("IsDisabled", False))
    except Exception:
        pass

    return {
        "total_plays": total_plays,
        "total_duration_ticks": total_duration_ticks,
        "active_users_24h": active_users_24h,
        "transcode_pct": transcode_pct,
        "total_storage_bytes": total_storage_bytes,
        "total_users": total_users,
        "disabled_users": disabled_users,
    }
