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

from fastapi import APIRouter, HTTPException, Query, Request, Response

from constants.portal_paths import IMAGE_PROXY_PATH
from core.rate_limit import ip_key, limiter
from core.url_safety import is_allowed_image_url
from services.portal import image_cache

logger = logging.getLogger("mediakeeper.api.image_proxy")
router = APIRouter()


@router.get(IMAGE_PROXY_PATH)
# High explicit per-IP limit instead of the global ``120/minute`` default.
# The Portal Home alone renders 100+ image tiles on first paint, so the 120
# default turned the tail of every load into 429s. ``1800/minute`` clears that
# burst with a wide margin while keeping a ceiling on this unauthenticated
# endpoint (each cache miss does an outbound TMDB fetch + a disk-cache write).
# This per-route limit overrides the default — and is honoured only because the
# SPA fallback is a 404 handler (see ``app_spa.py``) and no longer shadows
# slowapi's per-route lookup. Bytes are public TMDB CDN content, SSRF-guarded
# (``is_allowed_image_url``) and cached browser-side for 7 days.
@limiter.limit("1800/minute", key_func=ip_key)
async def proxy_image(
    request: Request,
    u: str = Query(..., description="Original TMDB image URL."),
):
    """Serve the requested image from disk, falling back to TMDB."""
    # Strict hostname check (urlparse-based) so userinfo bypasses
    # ``https://image.tmdb.org@evil.com/x`` and trailing-dot subdomain
    # tricks cannot reach the upstream client.
    if not is_allowed_image_url(u):
        raise HTTPException(status_code=400, detail="invalid_image_url")
    try:
        content, content_type = await image_cache.fetch_or_serve(u)
    except Exception as e:  # noqa: BLE001 -- upstream + defence-in-depth failures
        logger.warning("image_proxy: fetch failed for %s: %s", u, e)
        raise HTTPException(status_code=502, detail="upstream_unavailable") from e
    # 7-day immutable cache hint — image bytes are content-addressed
    # by the upstream URL, so the same query always yields the same
    # bytes. Lets browsers / Service Workers absorb repeated views
    # without bothering the backend.
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=604800, immutable"},
    )
