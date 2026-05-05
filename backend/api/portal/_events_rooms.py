"""MediaKeeper Events (private/public + invitations + cinema room)."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile
from core.database import get_db
from models.portal.profile import UserProfile
from models.user import User
from services.portal import mk_events as mk_svc
from services.portal.achievements import safe_check_all_achievements_in_new_session

router = APIRouter()


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone_required")
    return value.astimezone(timezone.utc)


class MKEventMedia(BaseModel):
    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    title: str = Field(..., max_length=300)
    poster_url: Optional[str] = None
    runtime_min: Optional[int] = None


class CreateMKEvent(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    kind: str = Field(..., pattern="^(private|public)$")
    tmdb_ids: list[MKEventMedia] = Field(..., min_length=1, max_length=20)
    scheduled_at: datetime
    comment: Optional[str] = Field(None, max_length=2000)
    invitees: Optional[list[int]] = None

    @field_validator("scheduled_at")
    @classmethod
    def _scheduled_at_must_be_aware(cls, value: datetime) -> datetime:
        return _aware_utc(value)


class UpdateMKEvent(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    tmdb_ids: Optional[list[MKEventMedia]] = None
    scheduled_at: Optional[datetime] = None
    comment: Optional[str] = Field(None, max_length=2000)

    @field_validator("scheduled_at")
    @classmethod
    def _scheduled_at_must_be_aware(cls, value: datetime | None) -> datetime | None:
        return _aware_utc(value)


class RespondPayload(BaseModel):
    decision: str = Field(..., pattern="^(accept|decline)$")


class RoomMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


def _err(result: dict) -> None:
    """Convert a service-returned error into an HTTPException."""
    if "error" not in result:
        return
    code_map = {
        "not_found": 404,
        "forbidden": 403,
        "not_invited": 403,
        "not_member": 403,
        "removed_user": 403,
    }
    code = code_map.get(result["error"], 400)
    raise HTTPException(status_code=code, detail=result["error"])


@router.post("/rooms")
async def create_mk_event(
    data: CreateMKEvent,
    background_tasks: BackgroundTasks,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await mk_svc.create_event(
        db, user.id,
        title=data.title,
        kind=data.kind,
        tmdb_ids=[m.model_dump() for m in data.tmdb_ids],
        scheduled_at=data.scheduled_at,
        comment=data.comment,
        invitees=data.invitees,
    )
    _err(result)
    background_tasks.add_task(
        safe_check_all_achievements_in_new_session,
        user.id,
        user.username,
        "event_created",
    )
    return result


@router.get("/rooms")
async def list_mk_events(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return {"items": await mk_svc.list_for_user(db, user.id)}


@router.get("/rooms/{event_id}")
async def get_mk_event(
    event_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    ev = await mk_svc.get_one(db, event_id, user.id)
    if not ev:
        raise HTTPException(status_code=404, detail="not_found")
    _err(ev)
    return ev


@router.patch("/rooms/{event_id}")
async def update_mk_event(
    event_id: int,
    data: UpdateMKEvent,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    payload = data.model_dump(exclude_unset=True)
    if "tmdb_ids" in payload and payload["tmdb_ids"] is not None:
        payload["tmdb_ids"] = [m.model_dump() if hasattr(m, "model_dump") else m
                                for m in payload["tmdb_ids"]]
    result = await mk_svc.update_event(db, event_id, user.id, **payload)
    _err(result)
    return result


@router.delete("/rooms/{event_id}")
async def cancel_mk_event(
    event_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await mk_svc.cancel_event(db, event_id, user.id)
    _err(result)
    return result


@router.post("/rooms/{event_id}/invite/{user_id}")
async def invite_mk_user(
    event_id: int,
    user_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await mk_svc.invite_user(db, event_id, user.id, user_id)
    _err(result)
    return result


@router.post("/rooms/{event_id}/respond")
async def respond_mk(
    event_id: int,
    data: RespondPayload,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await mk_svc.respond(db, event_id, user.id, data.decision)
    _err(result)
    return result


@router.post("/rooms/{event_id}/remove/{user_id}")
async def remove_mk_member(
    event_id: int,
    user_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await mk_svc.remove_member(db, event_id, user.id, user_id)
    _err(result)
    return result


@router.post("/rooms/{event_id}/enter")
async def enter_mk_room(
    event_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await mk_svc.enter_room(db, event_id, user.id)
    _err(result)
    return result


@router.get("/rooms/{event_id}/messages")
async def list_mk_messages(
    event_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await mk_svc.list_messages(db, event_id, user.id)
    _err(result)
    return result


@router.post("/rooms/{event_id}/messages")
async def post_mk_message(
    event_id: int,
    data: RoomMessage,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await mk_svc.post_message(db, event_id, user.id, data.content)
    _err(result)
    return result
