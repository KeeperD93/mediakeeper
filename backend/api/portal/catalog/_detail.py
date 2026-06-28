"""TMDB details + multi-search."""
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile
from core.database import get_db
from core.i18n import get_request_locale
from models.portal.profile import UserProfile
from models.user import User
from services.portal import discover as disc_svc
from services.portal.adult_filter import drop_adult
from services.portal.discover_details import get_person_filmography, get_collection
from services.portal.tmdb_search import search_with_cache
from services.tmdb import get_season_episodes, get_tv_seasons

router = APIRouter()

# Every endpoint below resolves its TMDB metadata language from the
# viewer's active locale (the ``X-MK-Locale`` header via get_request_locale),
# matching the discover routes — not the stored profile language.


@router.get("/videos/{media_type}/{tmdb_id}")
async def videos(
    media_type: str = Path(..., pattern="^(movie|tv)$"),
    tmdb_id: int = Path(...),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    return {"items": await disc_svc.get_media_videos(db, media_type, tmdb_id, language=locale)}


@router.get("/detail/{media_type}/{tmdb_id}")
async def media_detail(
    media_type: str = Path(..., pattern="^(movie|tv)$"),
    tmdb_id: int = Path(...),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    """Full details: cast, crew, budget, videos, recommendations.

    Metadata language follows the viewer's active locale (X-MK-Locale).
    """
    _, profile = up
    result = await disc_svc.get_full_details(db, media_type, tmdb_id, language=locale)
    if not result:
        raise HTTPException(status_code=404, detail="not_found")
    result["recommendations"] = drop_adult(result.get("recommendations"), bool(profile.hide_adult))
    return result


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1, max_length=200),
    page: int = Query(1, ge=1, le=5),
    available_only: bool = Query(False),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    _, profile = up
    items = await search_with_cache(
        db, q, page, available_only=available_only, language=locale,
    )
    return {"items": drop_adult(items, bool(profile.hide_adult))}


@router.get("/person/{person_id}")
async def person_filmography(
    person_id: int,
    role: str = Query("all", pattern="^(all|director|acting)$"),
    media: str = Query("all", pattern="^(all|movie|tv)$"),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    """Combined filmography of a person (as director and/or cast)."""
    _, profile = up
    result = await get_person_filmography(
        db, person_id, role=role, media_filter=media, language=locale,
    )
    result["items"] = drop_adult(result.get("items"), bool(profile.hide_adult))
    return result


@router.get("/collection/{collection_id}")
async def collection_detail(
    collection_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    """TMDB franchise / collection items."""
    _, profile = up
    result = await get_collection(db, collection_id, language=locale)
    result["items"] = drop_adult(result.get("items"), bool(profile.hide_adult))
    return result


# Portal-authenticated TMDB season/episode endpoints. Needed so the
# RequestModal can show per-episode checkboxes for TV series without
# requiring the main app auth (which portal-only users don't have).
@router.get("/tv/{tmdb_id}/seasons")
async def tv_seasons(
    tmdb_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    return await get_tv_seasons(tmdb_id, db, language=locale)


@router.get("/tv/{tmdb_id}/season/{season}")
async def tv_season_episodes(
    tmdb_id: int,
    season: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    return await get_season_episodes(tmdb_id, season, db, language=locale)
