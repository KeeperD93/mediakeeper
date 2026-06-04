"""Listes TMDB triviales : trending, popular, top-rated, oscars, provider…"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile
from core.database import get_db
from core.i18n import get_request_locale
from models.portal.profile import UserProfile
from models.user import User
from services.portal import discover as disc_svc

router = APIRouter()


@router.get("/trending")
async def trending(
    page: int = Query(1, ge=1, le=10),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_trending(db, page, language=locale)}


@router.get("/popular")
async def popular(
    page: int = Query(1, ge=1, le=10),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_popular_movies(db, page, language=locale)}


@router.get("/popular-tv")
async def popular_tv(
    page: int = Query(1, ge=1, le=10),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_popular_tv(db, page, language=locale)}


@router.get("/top-rated")
async def top_rated(
    page: int = Query(1, ge=1, le=10),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_top_rated(db, page, language=locale)}


@router.get("/oscars")
async def oscars(
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_oscar_winners(db, language=locale)}


@router.get("/family")
async def family(
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_family(db, language=locale)}


@router.get("/top-rated-year")
async def top_rated_year(
    page: int = Query(1, ge=1, le=10),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_top_rated_year(db, page, language=locale)}


@router.get("/provider/{provider_id}")
async def by_provider(
    provider_id: int,
    media_type: str = Query("movie", pattern="^(movie|tv)$"),
    page: int = Query(1, ge=1, le=10),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {
        "items": await disc_svc.get_by_provider(
            db, provider_id, media_type, page, language=locale,
        ),
    }


@router.get("/upcoming")
async def upcoming(
    page: int = Query(1, ge=1, le=10),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await disc_svc.get_upcoming(db, page, language=locale)}
