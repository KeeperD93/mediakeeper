"""Listes TMDB triviales : trending, popular, top-rated, oscars, provider…"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile
from core.database import get_db
from models.portal.profile import UserProfile
from models.user import User
from services.portal import discover as disc_svc

router = APIRouter()


@router.get("/trending")
async def trending(
    page: int = Query(1, ge=1, le=10),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_trending(db, page)}


@router.get("/popular")
async def popular(
    page: int = Query(1, ge=1, le=10),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_popular_movies(db, page)}


@router.get("/popular-tv")
async def popular_tv(
    page: int = Query(1, ge=1, le=10),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_popular_tv(db, page)}


@router.get("/top-rated")
async def top_rated(
    page: int = Query(1, ge=1, le=10),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_top_rated(db, page)}


@router.get("/oscars")
async def oscars(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_oscar_winners(db)}


@router.get("/family")
async def family(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_family(db)}


@router.get("/top-rated-year")
async def top_rated_year(
    page: int = Query(1, ge=1, le=10),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_top_rated_year(db, page)}


@router.get("/provider/{provider_id}")
async def by_provider(
    provider_id: int,
    media_type: str = Query("movie", pattern="^(movie|tv)$"),
    page: int = Query(1, ge=1, le=10),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_by_provider(db, provider_id, media_type, page)}


@router.get("/upcoming")
async def upcoming(
    page: int = Query(1, ge=1, le=10),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_upcoming(db, page)}
