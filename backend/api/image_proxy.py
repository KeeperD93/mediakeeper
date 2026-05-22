"""Public image proxy that serves cached TMDB posters / backdrops.

Mounted at ``/api/img`` outside the portal auth scope: the browser
hits it once per ``<img>`` and we want to keep the latency low
(no session check, no CSRF dance). The privacy surface is nil —
TMDB CDN images are themselves public assets.

See :mod:`services.portal.image_cache` for the storage logic and
the admin toggle.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Response

from core.url_safety import is_allowed_image_url
from services.portal import image_cache

logger = logging.getLogger("mediakeeper.api.image_proxy")
router = APIRouter()


@router.get("/api/img")
async def proxy_image(u: str = Query(..., description="Original TMDB image URL.")):
    """Serve the requested image from disk, falling back to TMDB."""
    # Strict hostname check (urlparse-based) so userinfo bypasses
    # ``https://image.tmdb.org@evil.com/x`` and trailing-dot subdomain
    # tricks cannot reach the upstream client.
    if not is_allowed_image_url(u):
        raise HTTPException(status_code=400, detail="invalid_image_url")
    try:
        content, content_type = await image_cache.fetch_or_serve(u)
    except Exception as e:  # noqa: BLE001 -- upstream failures
        logger.warning(f"image_proxy: fetch failed for {u}: {e}")
        raise HTTPException(status_code=502, detail="upstream_unavailable")
    # 7-day immutable cache hint — image bytes are content-addressed
    # by the upstream URL, so the same query always yields the same
    # bytes. Lets browsers / Service Workers absorb repeated views
    # without bothering the backend.
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=604800, immutable"},
    )
