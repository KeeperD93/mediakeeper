"""TMDB proxy endpoints (search + details)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.tmdb import (
    get_media_detail,
    get_season_episodes,
    get_tv_seasons,
    search_movie,
    search_tv,
)

router = APIRouter()


@router.get("/tmdb/search/movie")
async def tmdb_search_movie(q: str, language: str = None, year: int | None = None, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await search_movie(q, db, language=language, year=year)


@router.get("/tmdb/search/tv")
async def tmdb_search_tv(q: str, language: str = None, year: int | None = None, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await search_tv(q, db, language=language, year=year)


@router.get("/tmdb/tv/{tmdb_id}/seasons")
async def tmdb_seasons(tmdb_id: int, language: str = None, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await get_tv_seasons(tmdb_id, db, language=language)


@router.get("/tmdb/tv/{tmdb_id}/season/{season}")
async def tmdb_episodes(tmdb_id: int, season: int, language: str = None, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await get_season_episodes(tmdb_id, season, db, language=language)


@router.get("/tmdb/detail/{media_type}/{tmdb_id}")
async def tmdb_detail(media_type: str, tmdb_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    """Return the full details of a movie or series (overview, backdrop, genres, runtime, ...)."""
    if media_type not in ("movie", "tv"):
        return {"error": "invalid_media_type"}
    return await get_media_detail(media_type, tmdb_id, db)
