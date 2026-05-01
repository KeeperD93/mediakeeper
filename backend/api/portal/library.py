"""Portal available endpoints: Emby library browsing."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_current_profile
from services.portal import available as avail_svc

router = APIRouter(prefix="/library", tags=["portal-available"])


@router.get("/recent")
async def recently_added(
    limit: int = Query(20, ge=1, le=50),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await avail_svc.get_recently_added(db, limit)}


@router.get("/recommended")
async def recommended(
    limit: int = Query(20, ge=1, le=50),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await avail_svc.get_recommended(db, limit)}


@router.get("/continue")
async def continue_watching(
    limit: int = Query(10, ge=1, le=30),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await avail_svc.get_continue_watching(db, limit=limit)}


@router.get("/genre/{genre_id}")
async def by_genre(
    genre_id: str,
    limit: int = Query(20, ge=1, le=50),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await avail_svc.get_by_genre(db, genre_id, limit)}


@router.get("/surprise")
async def surprise_pool(
    kind: str = Query(..., pattern="^(movie|tv|manga|documentary)$"),
    limit: int = Query(50, ge=10, le=100),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Random pool of Emby items used by the Surprise overlay to power
    its reveal animation. The frontend asks for a fresh pool every
    time the overlay opens so the pick feels genuinely random.
    """
    return {"items": await avail_svc.get_surprise_pool(db, kind, limit)}
