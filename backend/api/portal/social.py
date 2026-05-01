"""Portal social endpoints: ratings, reminders.

User-list endpoints have been moved to ``api.portal.lists`` — kept here
only: rating a media, liking a rating, release reminders.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_current_profile
from services.portal import social as social_svc

router = APIRouter(prefix="/social", tags=["portal-social"])


class RateMedia(BaseModel):
    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    rating: int = Field(..., ge=1, le=5)
    review: Optional[str] = Field(None, max_length=5000)


class AddReminder(BaseModel):
    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    release_date: Optional[str] = None


@router.post("/ratings")
async def rate(
    data: RateMedia,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return await social_svc.rate_media(db, user.id, data.model_dump())


@router.get("/ratings/{tmdb_id}/{media_type}")
async def get_ratings(
    tmdb_id: int,
    media_type: str,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await social_svc.get_media_ratings(db, tmdb_id, media_type)}


@router.post("/ratings/{rating_id}/like")
async def toggle_like(
    rating_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return await social_svc.toggle_rating_like(db, rating_id, user.id)


# ── Reminders ──

@router.get("/reminders")
async def get_reminders(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return {"items": await social_svc.get_user_reminders(db, user.id)}


@router.post("/reminders")
async def add_reminder(
    data: AddReminder,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await social_svc.add_reminder(db, user.id, data.tmdb_id, data.media_type)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/reminders/{tmdb_id}")
async def remove_reminder(
    tmdb_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return await social_svc.remove_reminder(db, user.id, tmdb_id)
