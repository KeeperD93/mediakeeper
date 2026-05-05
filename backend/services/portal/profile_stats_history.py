"""User-requests carousel + paginated variants for the profile page.

The recent-watches logic lives in a sibling module (``profile_stats_recent``)
to keep both files under the 300-line rule. Import surface stays the
same so existing callers don't change.
"""
import logging
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.playback_stats import PlaybackSession
from services.portal.personal import _playback_user_filter
from services.portal.profile_stats_recent import fetch_recent_watches  # re-export
from services.portal.profile_stats_emby import (
    _bulk_fetch_emby_info,
    _find_series_emby_id,
)
from services.settings import get_active_media_source

logger = logging.getLogger("mediakeeper.portal.profile_stats")

__all__ = [
    "fetch_recent_watches",
    "fetch_my_requests",
    "get_watch_history_paginated",
    "get_my_requests_paginated",
]


async def fetch_my_requests(db: AsyncSession, user: User) -> list[dict]:
    """Last 20 requests created by the user."""
    my_requests: list[dict] = []
    try:
        result = await db.execute(
            select(MediaRequest)
            .where(MediaRequest.user_id == user.id)
            .order_by(desc(MediaRequest.created_at))
            .limit(20)
        )
        for req in result.scalars().all():
            my_requests.append({
                "id": req.id,
                "tmdb_id": req.tmdb_id,
                "media_type": req.media_type,
                "title": req.title,
                "year": req.year,
                "poster_url": req.poster_url or "",
                "status": req.status,
                "retry_count": req.retry_count or 0,
                "reject_reason": req.reject_reason,
                "created_at": req.created_at.isoformat() if req.created_at else None,
            })
    except Exception as e:
        logger.debug(f"[PROFILE] requests error: {e}")
    return my_requests


async def get_watch_history_paginated(
    db: AsyncSession, user: User, profile: UserProfile,
    page: int = 1, page_size: int = 40,
) -> dict:
    """Paginated watch history, episodes resolved to series posters."""
    user_filter = _playback_user_filter(user, profile)
    offset = (page - 1) * page_size

    result = await db.execute(
        select(
            PlaybackSession.item_name,
            PlaybackSession.item_id,
            PlaybackSession.item_type,
            PlaybackSession.series_name,
            PlaybackSession.started_at,
        )
        .where(user_filter)
        .order_by(desc(PlaybackSession.started_at))
        .offset(offset)
        .limit(page_size + 1)
    )
    rows = result.all()
    has_more = len(rows) > page_size
    rows = rows[:page_size]

    emby_url = emby_key = ""
    source = await get_active_media_source(db)
    if source and source.get("source") in ("emby", "jellyfin"):
        emby_url = source.get("url", "").rstrip("/")
        emby_key = source.get("api_key", "")

    seen = set()
    candidates: list[dict] = []
    series_cache: dict[str, str] = {}
    for r in rows:
        # Same item-type guard as the carousel: drop intros (Audio /
        # Video typed by Emby) and loose Episode rows without a parent
        # series, which both render as orphan posters in the grid.
        if r.item_type not in ("Movie", "Episode"):
            continue
        is_ep = r.item_type == "Episode"
        if is_ep and not r.series_name:
            continue
        title = r.series_name if is_ep else r.item_name
        if not title or title in seen:
            continue
        seen.add(title)

        poster_id = r.item_id
        if is_ep and emby_url and emby_key:
            cached = series_cache.get(r.series_name)
            if cached is None:
                cached = await _find_series_emby_id(r.series_name, emby_url, emby_key) or ""
                series_cache[r.series_name] = cached
            if not cached:
                continue
            poster_id = cached
        candidates.append({
            "title": title,
            "emby_item_id": poster_id,
            "poster_url": f"/api/emby/image/{poster_id}?type=Primary" if poster_id else "",
            "media_type": "tv" if is_ep else "movie",
            "watched_at": r.started_at.isoformat() if r.started_at else None,
        })

    # Bulk-resolve TMDB ids + Primary image presence so we can drop
    # custom rips with no provider metadata or missing artwork.
    ids = [c["emby_item_id"] for c in candidates if c["emby_item_id"]]
    info = await _bulk_fetch_emby_info(ids, emby_url, emby_key)

    # "Watched" vs "In progress" tag — uses Emby UserData.Played as
    # the authoritative signal (same as the profile carousel).
    from services.portal.profile_stats_emby import resolve_emby_user_id
    from services.portal.profile_stats_recent import _series_watch_status
    from core.http_client import get_internal_client

    emby_uid = await resolve_emby_user_id(db, user_filter) if emby_url else None
    movie_ids = [c["emby_item_id"] for c in candidates if c["media_type"] == "movie" and c["emby_item_id"]]
    movie_played: dict[str, bool] = {}
    if movie_ids and emby_url and emby_uid:
        try:
            res = await get_internal_client().get(
                f"{emby_url}/Users/{emby_uid}/Items",
                params={"Ids": ",".join(movie_ids), "Fields": "UserData"},
                headers={"X-Emby-Token": emby_key}, timeout=10.0,
            )
            if res.status_code == 200:
                for item in res.json().get("Items", []):
                    movie_played[item.get("Id", "")] = bool((item.get("UserData") or {}).get("Played"))
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass

    cleaned: list[dict] = []
    series_status_cache: dict[str, str] = {}
    for c in candidates:
        d = info.get(c["emby_item_id"]) or {}
        tmdb_id = d.get("tmdb_id")
        if not tmdb_id or not d.get("has_image", False):
            continue
        if c["media_type"] == "movie":
            status = "watched" if movie_played.get(c["emby_item_id"]) else "in_progress"
        else:
            sname = c["title"]
            cached = series_status_cache.get(sname)
            if cached is None:
                cached = await _series_watch_status(
                    db, user_filter, [], sname, c["emby_item_id"], emby_url, emby_key,
                )
                series_status_cache[sname] = cached
            status = cached
        c["tmdb_id"] = tmdb_id
        c["id"] = tmdb_id
        c["watch_status"] = status
        c["availability"] = "full"
        cleaned.append(c)

    return {"items": cleaned, "page": page, "has_more": has_more}


async def get_my_requests_paginated(
    db: AsyncSession, user: User, page: int = 1, page_size: int = 40,
) -> dict:
    """Paginated requests for the current user."""
    offset = (page - 1) * page_size

    result = await db.execute(
        select(MediaRequest)
        .where(MediaRequest.user_id == user.id)
        .order_by(desc(MediaRequest.created_at))
        .offset(offset)
        .limit(page_size + 1)
    )
    rows = result.scalars().all()
    has_more = len(rows) > page_size
    rows = rows[:page_size]

    items = [{
        "id": req.tmdb_id,
        "tmdb_id": req.tmdb_id,
        "title": req.title,
        "year": req.year,
        "media_type": req.media_type,
        "poster_url": req.poster_url or "",
        "poster": req.poster_url or "",
        "_request_status": req.status,
        "_retry_count": req.retry_count or 0,
        "_reject_reason": req.reject_reason,
        "created_at": req.created_at.isoformat() if req.created_at else None,
    } for req in rows]

    return {"items": items, "page": page, "has_more": has_more}
