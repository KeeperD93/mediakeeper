"""
    Portal trailer endpoints.

- ``GET /api/portal/trailers/resolve`` runs the cascade and returns the
  best available trailer descriptor for a given media.
- ``GET /api/portal/trailers/emby/{trailer_id}`` proxies an Emby local
  trailer file so the private Emby URL never leaks to the browser.
"""
import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.http_client import get_internal_client
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_current_profile
from services.portal.trailers import resolve_trailer, stream_emby_trailer

router = APIRouter(prefix="/trailers", tags=["portal-trailers"])
logger = logging.getLogger("mediakeeper.portal.trailers")


@router.get("/random")
async def random_trailers(
    limit: int = Query(10, ge=1, le=30),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Random pool of trailer keys for the cinema room amwellt screen.

    Picks a handful of recently-added Emby items, runs the trailer
    cascade for each, and returns the YouTube keys (or Emby URLs) so
    the room can cycle through them while users wait for the show.
    """
    from services.portal.available import get_recently_added
    items = await get_recently_added(db, limit=limit * 2)
    _, profile = up
    user_lang = (profile.language or "en").split("-")[0].lower()

    # Resolve trailers concurrently — each call is an independent Emby +
    # TMDB cascade, so sequencing them used to cost ≈ n × ~300 ms. We
    # still only return the first ``limit`` successful keys, in the
    # original order of ``items``.
    candidates = [it for it in items if it.get("tmdb_id")]

    async def _resolve_one(it):
        try:
            return await resolve_trailer(
                db, it.get("media_type", "movie"), int(it["tmdb_id"]),
                user_lang, emby_item_id=it.get("emby_item_id"),
            )
        except Exception:
            return None

    resolved = await asyncio.gather(*(_resolve_one(it) for it in candidates))

    out: list[dict] = []
    for it, tr in zip(candidates, resolved):
        if len(out) >= limit:
            break
        if tr and tr.get("key"):
            out.append({"key": tr["key"], "title": it.get("title"), "source": tr.get("source")})
    return {"items": out}


@router.get("/resolve")
async def resolve(
    media_type: str = Query(..., pattern="^(movie|tv)$"),
    tmdb_id: int = Query(..., gt=0),
    emby_item_id: str | None = Query(None),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve the best trailer for a given media using the cascade.
    The user's preferred language is read from their Portal profile.
    """
    _, profile = up
    user_lang = (profile.language or "en").split("-")[0].lower()
    try:
        trailer = await resolve_trailer(
            db, media_type, tmdb_id, user_lang, emby_item_id=emby_item_id
        )
    except Exception as e:
        logger.warning(f"[TRAILERS] resolve failed: {e}")
        trailer = None
    return {"trailer": trailer}


@router.get("/emby/{trailer_id}")
async def proxy_emby_trailer(
    trailer_id: str,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream an Emby local trailer through the backend.

    This protects the private Emby URL and API key — the browser only
    ever sees the MediaKeeper origin, and authentication is enforced
    via the existing Portal profile dependency.
    """
    info = await stream_emby_trailer(db, trailer_id)
    if not info or not info.get("url"):
        raise HTTPException(status_code=404, detail="trailer_not_available")

    upstream_url = info["url"]
    client = get_internal_client()

    async def iterator():
        try:
            async with client.stream("GET", upstream_url, timeout=30.0) as resp:
                if resp.status_code != 200:
                    return
                async for chunk in resp.aiter_bytes():
                    yield chunk
        except httpx.HTTPError as e:
            logger.warning(f"[TRAILERS] proxy stream error: {e}")
            return

    # Emby usually returns video/mp4; we don't introspect to keep it simple.
    return StreamingResponse(iterator(), media_type="video/mp4")
