"""MediaKeeper Events (private/public + invitations + cinema room)."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile, get_request_lang
from core.database import get_db
from core.rate_limit import limiter, portal_user_or_ip_key
from models.portal.profile import UserProfile
from models.user import User
from services.portal import mk_events as mk_svc
from services.portal.achievements import safe_check_all_achievements_in_new_session
from services.portal.mk_events_marathon import (
    MarathonError,
    advance_marathon_step,
    compute_marathon_progress,
)
from services.portal.mk_events_presence import (
    PresenceError,
    advance_self_step,
    heartbeat as presence_heartbeat,
    leave_room as presence_leave_room,
)

router = APIRouter()


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone_required")
    return value.astimezone(timezone.utc)


class MKEventMedia(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    title: str = Field(..., max_length=300)
    poster_url: Optional[str] = None
    runtime_min: Optional[int] = None


class CreateMKEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    kind: str = Field(..., pattern="^(private|public)$")
    tmdb_ids: list[MKEventMedia] = Field(..., min_length=1, max_length=20)
    scheduled_at: datetime
    comment: Optional[str] = Field(None, max_length=2000)
    invitees: Optional[list[int]] = Field(default=None, max_length=100)
    # Per-event capacity (5/10/15/20 — radio chips on the create form).
    # The actual [min, max] window is admin-tunable and re-checked
    # server-side in ``create_event`` against the current bounds.
    max_participants: int = Field(..., ge=5, le=20)

    @field_validator("scheduled_at")
    @classmethod
    def _scheduled_at_must_be_aware(cls, value: datetime) -> datetime:
        return _aware_utc(value)

    @field_validator("max_participants")
    @classmethod
    def _max_participants_step_5(cls, value: int) -> int:
        if value % 5 != 0:
            raise ValueError("max_participants_must_be_multiple_of_5")
        return value


class UpdateMKEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    tmdb_ids: Optional[list[MKEventMedia]] = None
    scheduled_at: Optional[datetime] = None
    comment: Optional[str] = Field(None, max_length=2000)

    @field_validator("scheduled_at")
    @classmethod
    def _scheduled_at_must_be_aware(cls, value: datetime | None) -> datetime | None:
        return _aware_utc(value)


class RespondPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(..., pattern="^(accept|decline)$")


class RoomMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(..., min_length=1, max_length=2000)


def _err(result: dict) -> None:
    """Convert a service-returned error into an HTTPException."""
    if "error" not in result:
        return
    code_map = {
        "not_found": 404,
        "forbidden": 403,
        "not_invited": 403,
        "not_invitable": 403,
        "not_member": 403,
        "removed_user": 403,
    }
    code = code_map.get(result["error"], 400)
    raise HTTPException(status_code=code, detail=result["error"])


@router.get("/rooms/capacity-bounds")
async def get_room_capacity_bounds(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Surface the admin-tunable per-event capacity bounds (min/max +
    step) so the create-event form can render its radio chips without
    needing admin access to ``/admin/settings``."""
    from services.portal.admin import (
        PORTAL_EVENT_CAPACITY_STEP,
        get_event_capacity_bounds,
    )

    min_cap, max_cap = await get_event_capacity_bounds(db)
    return {
        "min": min_cap,
        "max": max_cap,
        "step": PORTAL_EVENT_CAPACITY_STEP,
    }


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
        max_participants=data.max_participants,
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


class AdvanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Client tells the server which step it believes is in flight. The
    # server rejects with 409 if its locked row says otherwise (another
    # client has already advanced the marathon).
    expected_step: int


def _raise_marathon(err: MarathonError) -> None:
    detail: dict[str, object] = {"error": err.detail}
    if err.payload:
        detail.update(err.payload)
    raise HTTPException(status_code=err.status_code, detail=detail)


@router.get("/rooms/{event_id}/marathon-progress")
@limiter.limit("60/minute", key_func=portal_user_or_ip_key)
async def get_marathon_progress(
    request: Request,
    event_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_lang),
):
    # The cinema room polls this endpoint every 5 s while a marathon is
    # live, plus per-user (chat / bubbles / enter_room / availability
    # …) — the global 120/min IP bucket drowns under that aggregate and
    # spits 429s after a refresh. A dedicated 60/min per-user limit
    # gives the poller 12× more headroom than it actually needs while
    # still capping a runaway client.
    user, _ = up
    try:
        return await compute_marathon_progress(db, event_id, user.id, lang)
    except MarathonError as err:
        _raise_marathon(err)


@router.post("/rooms/{event_id}/advance")
async def advance_marathon(
    event_id: int,
    data: AdvanceRequest,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_lang),
):
    user, _ = up
    try:
        return await advance_marathon_step(
            db, event_id, user.id, data.expected_step, lang,
        )
    except MarathonError as err:
        _raise_marathon(err)


def _raise_presence(err: PresenceError) -> None:
    raise HTTPException(
        status_code=err.status_code, detail={"error": err.detail},
    )


@router.post("/rooms/{event_id}/heartbeat")
# Heartbeat is called every 5 s per open cinema tab; 60/min per-user
# leaves room for one missed tick + a quick reconnect without 429s.
@limiter.limit("60/minute", key_func=portal_user_or_ip_key)
async def heartbeat_mk_room(
    request: Request,
    event_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    try:
        return await presence_heartbeat(db, event_id, user.id)
    except PresenceError as err:
        _raise_presence(err)


@router.post("/rooms/{event_id}/leave")
async def leave_mk_room(
    event_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    try:
        return await presence_leave_room(db, event_id, user.id)
    except PresenceError as err:
        _raise_presence(err)


@router.post("/rooms/{event_id}/advance-self")
async def advance_self_mk_room(
    event_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    try:
        return await advance_self_step(db, event_id, user.id)
    except PresenceError as err:
        _raise_presence(err)


@router.get("/rooms/{event_id}/messages")
async def list_mk_messages(
    event_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_lang),
):
    user, _ = up
    result = await mk_svc.list_messages(db, event_id, user.id, lang=lang)
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
