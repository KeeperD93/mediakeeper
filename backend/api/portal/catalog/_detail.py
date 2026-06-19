"""TMDB details + multi-search."""
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile
from core.database import get_db
from models.portal.profile import UserProfile
from models.user import User
from services.portal import discover as disc_svc
from services.portal.adult_filter import drop_adult
from services.portal.discover_details import get_person_filmography, get_collection
from services.portal.tmdb_search import search_with_cache
from services.tmdb import get_season_episodes, get_tv_seasons

router = APIRouter()


@router.get("/videos/{media_type}/{tmdb_id}")
async def videos(
    media_type: str = Path(..., pattern="^(movie|tv)$"),
    tmdb_id: int = Path(...),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_media_videos(db, media_type, tmdb_id)}


@router.get("/detail/{media_type}/{tmdb_id}")
async def media_detail(
    media_type: str = Path(..., pattern="^(movie|tv)$"),
    tmdb_id: int = Path(...),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Full details: cast, crew, budget, videos, recommendations.

    Metadata language follows the user's Portal profile preference.
    """
    _, profile = up
    user_lang = (profile.language or "").split("-")[0].lower() or None
    result = await disc_svc.get_full_details(db, media_type, tmdb_id, language=user_lang)
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
):
    _, profile = up
    user_lang = (profile.language or "").split("-")[0].lower() or None
    items = await search_with_cache(
        db, q, page, available_only=available_only, language=user_lang,
    )
    return {"items": drop_adult(items, bool(profile.hide_adult))}


@router.get("/person/{person_id}")
async def person_filmography(
    person_id: int,
    role: str = Query("all", pattern="^(all|director|acting)$"),
    media: str = Query("all", pattern="^(all|movie|tv)$"),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Combined filmography of a person (as director and/or cast)."""
    _, profile = up
    result = await get_person_filmography(db, person_id, role=role, media_filter=media)
    result["items"] = drop_adult(result.get("items"), bool(profile.hide_adult))
    return result


@router.get("/collection/{collection_id}")
async def collection_detail(
    collection_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """TMDB franchise / collection items."""
    _, profile = up
    result = await get_collection(db, collection_id)
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
):
    _, profile = up
    user_lang = (profile.language or "").split("-")[0].lower() or None
    return await get_tv_seasons(tmdb_id, db, language=user_lang)


@router.get("/tv/{tmdb_id}/season/{season}")
async def tv_season_episodes(
    tmdb_id: int,
    season: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    _, profile = up
    user_lang = (profile.language or "").split("-")[0].lower() or None
    return await get_season_episodes(tmdb_id, season, db, language=user_lang)
