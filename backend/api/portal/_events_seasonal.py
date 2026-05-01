"""Seasonal events + watch parties (community challenges)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile, require_admin
from core.database import get_db
from models.portal.profile import UserProfile
from models.user import User
from services.portal import events as events_svc

router = APIRouter()


class CreateEvent(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=2000)
    start_date: datetime
    end_date: datetime
    genre_filter: Optional[list[int]] = None
    target_count: int = Field(10, ge=1, le=1000)
    badge_id: Optional[str] = None


class CreateParty(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    tmdb_id: Optional[int] = None
    media_type: Optional[str] = Field(None, pattern="^(movie|tv)$")
    scheduled_at: datetime
    max_participants: int = Field(20, ge=2, le=100)


# ── Seasonal events ──

@router.get("/seasonal")
async def active_events(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await events_svc.get_active_events(db)}


@router.get("/seasonal/{event_id}/progress")
async def event_progress(
    event_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return await events_svc.get_event_progress(db, event_id, user.id)


@router.post("/seasonal")
async def create_event(
    data: CreateEvent,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user, _ = admin
    return await events_svc.create_seasonal_event(db, user.id, data.model_dump())


# ── Watch parties ──

@router.get("/parties")
async def upcoming_parties(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await events_svc.list_upcoming_parties(db)}


@router.post("/parties")
async def create_party(
    data: CreateParty,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return await events_svc.create_watch_party(db, user.id, data.model_dump())


@router.post("/parties/{party_id}/join")
async def join_party(
    party_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await events_svc.join_party(db, party_id, user.id)
    if "error" in result:
        code = 404 if result["error"] == "not_found" else 400
        raise HTTPException(status_code=code, detail=result["error"])
    return result


@router.post("/parties/{party_id}/leave")
async def leave_party(
    party_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return await events_svc.leave_party(db, party_id, user.id)
