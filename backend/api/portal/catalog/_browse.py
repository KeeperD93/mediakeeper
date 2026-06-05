"""Category/provider pagination + TMDB watch-providers debug helper."""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile
from core.database import get_db
from core.i18n import get_request_locale
from models.portal.profile import UserProfile
from models.user import User
from services.portal import discover as disc_svc

logger = logging.getLogger("mediakeeper.api.portal.catalog")
router = APIRouter()


@router.get("/category/{category}")
async def browse_category(
    category: str,
    page: int = Query(1, ge=1, le=500),
    sort: str = Query("popularity", pattern="^(popularity|release|rating)$"),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Paginated browse for a UX category (movies, series, …).

    ``recently-added`` is a playback-source concept, not a catalogue one,
    so it is NOT routed through TMDB Discover.
    """
    if category == "recently-added":
        from services.portal import available as avail_svc
        return await avail_svc.get_recently_added_paginated(db, page=page)

    if category == "watch-history":
        from services.portal.profile_stats import get_watch_history_paginated
        user, profile = up
        return await get_watch_history_paginated(db, user, profile, page=page)

    if category == "my-requests":
        from services.portal.profile_stats import get_my_requests_paginated
        user, _ = up
        return await get_my_requests_paginated(db, user, page=page)

    _, profile = up
    return await disc_svc.discover_category(
        db, category, page=page, sort=sort, language=locale,
        include_adult=not bool(profile.hide_adult),
    )


@router.get("/browse-provider/{provider_id}")
async def browse_provider(
    provider_id: int,
    page: int = Query(1, ge=1, le=500),
    sort: str = Query("popularity", pattern="^(popularity|release|rating)$"),
    region: str = Query("FR", min_length=2, max_length=4),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Paginated browse for a watch provider (Netflix, Prime, …)."""
    _, profile = up
    return await disc_svc.discover_provider(
        db, provider_id, page=page, sort=sort, language=locale, region=region,
        include_adult=not bool(profile.hide_adult),
    )


@router.get("/watch-providers")
async def watch_providers(
    region: str = Query("FR", min_length=2, max_length=4),
    media_type: str = Query("movie", pattern="^(movie|tv)$"),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Debug/admin helper: list all TMDB watch providers for a region + media type.

    Usage: ``GET /api/portal/catalog/watch-providers?region=FR&media_type=movie``
    """
    from core.http_client import get_external_client
    from services.tmdb import TMDB_BASE, _get_tmdb_key, _tmdb_headers_sync

    api_key = await _get_tmdb_key(db)
    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/watch/providers/{media_type}",
            params={"watch_region": region, "language": "fr-FR"},
            headers=_tmdb_headers_sync(api_key),
        )
        if res.status_code != 200:
            return {"error": f"TMDB returned {res.status_code}", "items": []}
        results = (res.json() or {}).get("results", [])
        items = [
            {
                "provider_id": r.get("provider_id"),
                "provider_name": r.get("provider_name"),
                "display_priority": r.get("display_priorities", {}).get(region, r.get("display_priority")),
            }
            for r in results
        ]
        items.sort(key=lambda x: (x.get("display_priority") or 999, x.get("provider_name") or ""))
        return {"region": region, "media_type": media_type, "count": len(items), "items": items}
    except Exception:
        logger.exception("[catalog] watch_providers failed")
        return {"error": "watch_providers_failed", "items": []}
