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
from core.i18n import get_request_locale
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_current_profile
from services.portal.available_localize import localize_emby_items
from services.portal.trailers import resolve_trailer, resolve_trailers, stream_emby_trailer

router = APIRouter(prefix="/trailers", tags=["portal-trailers"])
logger = logging.getLogger("mediakeeper.portal.trailers")

# Defence-in-depth cap on the proxied stream. ``stream_emby_trailer``
# already restricts this proxy to real trailers (short clips), so this
# only guards against a pathologically large upstream file.
_MAX_TRAILER_BYTES = 1024 * 1024 * 1024  # 1 GiB


@router.get("/random")
async def random_trailers(
    limit: int = Query(10, ge=1, le=30),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    """
    Random pool of trailer keys for the cinema room ambient screen.

    Picks a handful of recently-added Emby items, runs the trailer
    cascade for each, and returns the YouTube keys (or Emby URLs) so
    the room can cycle through them while users wait for the show.
    Titles and the trailer language follow the viewer's active locale
    (X-MK-Locale).
    """
    from services.portal.available import get_recently_added
    items = await get_recently_added(db, limit=limit * 2)
    items = await localize_emby_items(db, items, locale)

    # Resolve trailers concurrently — each call is an independent Emby +
    # TMDB cascade, so sequencing them used to cost ≈ n × ~300 ms. We
    # still only return the first ``limit`` successful keys, in the
    # original order of ``items``.
    candidates = [it for it in items if it.get("tmdb_id")]

    async def _resolve_one(it):
        try:
            return await resolve_trailer(
                db, it.get("media_type", "movie"), int(it["tmdb_id"]),
                locale, emby_item_id=it.get("emby_item_id"),
            )
        except Exception:
            return None

    resolved = await asyncio.gather(*(_resolve_one(it) for it in candidates))

    out: list[dict] = []
    for it, tr in zip(candidates, resolved):
        if len(out) >= limit:
            break
        if tr and tr.get("key"):
            out.append({
                "key": tr["key"],
                "title": it.get("title"),
                "source": tr.get("source"),
                "emby_item_id": it.get("emby_item_id") or None,
                "tmdb_id": int(it["tmdb_id"]) if it.get("tmdb_id") else None,
                "media_type": it.get("media_type", "movie"),
                "emby_url": it.get("emby_url") or None,
            })
    return {"items": out}


@router.get("/resolve")
async def resolve(
    media_type: str = Query(..., pattern="^(movie|tv)$"),
    tmdb_id: int = Query(..., gt=0),
    emby_item_id: str | None = Query(None, pattern="^[A-Za-z0-9]+$"),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    """
    Resolve trailers for a given media using the cascade.

    Returns the best trailer (``trailer``) plus the full ranked candidate
    list (``candidates``) so the player can fall back to another one when
    the first is region-blocked by the provider. ``candidates[0] == trailer``.
    The trailer language follows the viewer's active locale (X-MK-Locale).
    """
    try:
        candidates = await resolve_trailers(
            db, media_type, tmdb_id, locale, emby_item_id=emby_item_id
        )
    except Exception as e:
        logger.warning("[TRAILERS] resolve failed: %s", e)
        candidates = []
    return {"trailer": candidates[0] if candidates else None, "candidates": candidates}


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
    try:
        resp = await client.send(
            client.build_request("GET", upstream_url, timeout=30.0), stream=True
        )
    except httpx.HTTPError as e:
        logger.warning("[TRAILERS] proxy connect error: %s", e)
        raise HTTPException(status_code=502, detail="trailer_upstream_error") from e
    if resp.status_code != 200:
        await resp.aclose()
        raise HTTPException(status_code=404, detail="trailer_not_available")
    # Propagate Emby's real Content-Type (mp4/mkv/webm) instead of assuming mp4.
    content_type = resp.headers.get("content-type") or "video/mp4"

    async def iterator():
        streamed = 0
        try:
            async for chunk in resp.aiter_bytes():
                streamed += len(chunk)
                if streamed > _MAX_TRAILER_BYTES:
                    logger.warning(
                        "[TRAILERS] trailer %s exceeded the %d-byte cap; truncating",
                        trailer_id, _MAX_TRAILER_BYTES,
                    )
                    break
                yield chunk
        except httpx.HTTPError as e:
            logger.warning("[TRAILERS] proxy stream error: %s", e)
        finally:
            await resp.aclose()

    return StreamingResponse(iterator(), media_type=content_type)
