"""MediaKeeper admin endpoints for Portal users & chat moderation.

Protected by the regular MediaKeeper ``mk_token`` cookie via
``get_current_user`` — admin-side tooling, not part of the Portal
user-facing API.

Exposed routes (mounted under ``/api/portal/admin/requests``):

- ``POST   /users/import``      — batch import Emby users
- ``GET    /users``             — list every UserProfile
- ``PATCH  /users/{id}``        — update active flag, role, chat settings
- ``POST   /enter``             — grant current MK admin a Portal session
- ``GET    /chat/reports``      — list open chat moderation reports
- ``POST   /chat/reports/{id}/dismiss`` — mark report handled
- ``DELETE /chat/messages/{id}``— soft-delete a chat message
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.auth import get_current_user, grant_portal_admin_session, require_csrf
from services.portal._rank_tiers import tier_for_level
from services.portal.user_import import import_emby_users

router = APIRouter(prefix="/api/portal/admin/requests", tags=["portal-admin-requests"])
logger = logging.getLogger("mediakeeper.api.portal_admin_requests")


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

@router.post("/users/import")
async def import_users(
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pull the list of users from Emby and create matching Portal profiles."""
    result = await import_emby_users(db)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# List / manage
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return every Portal profile with its MediaKeeper user row joined."""
    rows = await db.execute(
        select(UserProfile, User)
        .join(User, User.id == UserProfile.user_id)
        .order_by(UserProfile.display_name)
    )
    items = []
    for profile, user in rows.all():
        items.append({
            "id": profile.id,
            "user_id": user.id,
            "username": user.username,
            "display_name": profile.display_name,
            "avatar_url": profile.avatar_url,
            "role": profile.role,
            "account_active": profile.account_active,
            "chat_enabled": profile.chat_enabled,
            "is_public": profile.is_public,
            "forced_public": profile.forced_public,
            "level": profile.level,
            "tier": tier_for_level(profile.level or 1),
            "xp": profile.xp,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        })
    return {"items": items}


class ProfileAdminUpdate(BaseModel):
    account_active: Optional[bool] = None
    role: Optional[str] = Field(None, pattern="^(viewer|moderator|admin)$")
    chat_enabled: Optional[bool] = None
    forced_public: Optional[bool] = None


@router.patch("/users/{profile_id}")
async def update_user(
    profile_id: int,
    data: ProfileAdminUpdate,
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin update: activate/disable, change role, mute chat, force visibility."""
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.id == profile_id))
    ).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="profile_not_found")

    payload = data.model_dump(exclude_none=True)
    for key, value in payload.items():
        setattr(profile, key, value)
    db.add(profile)
    await db.commit()
    return {"ok": True}


@router.post("/enter")
async def enter_as_admin(
    request: Request,
    response: Response,
    csrf_protected: None = Depends(require_csrf),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Super-admin bypass: grants the currently logged-in MediaKeeper
    user a Portal session without going through Emby authentication.

    - Creates a ``UserProfile`` on the fly if none exists (role=admin,
      account_active=True). This makes the MK admin a first-class
      Portal admin without having to import themselves from Emby.
    - Always issues the ``rq_token`` cookie with ``scope=portal``.
    - The ``mk_token`` cookie is untouched, so the admin keeps access
      to the MediaKeeper backoffice in parallel.
    """
    await grant_portal_admin_session(request, response, current, db)
    logger.info("[PORTAL_ADMIN] Admin Portal session granted for user=%s", current.username)
    return {"ok": True}


@router.get("/chat/reports")
async def list_chat_reports(
    only_open: bool = True,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return every chat report, newest first. ``only_open=true`` (the
    default) filters out reports that have already been dismissed
    or actioned, so the bell only surfaces what needs attention.
    """
    from models.portal.chat import ChatReport, ChatMessage
    from models.portal.profile import UserProfile

    stmt = (
        select(
            ChatReport,
            ChatMessage.content,
            ChatMessage.user_id.label("author_id"),
            ChatMessage.deleted.label("message_deleted"),
            UserProfile.display_name.label("author_name"),
        )
        .join(ChatMessage, ChatMessage.id == ChatReport.message_id)
        .outerjoin(UserProfile, UserProfile.user_id == ChatMessage.user_id)
        .order_by(ChatReport.created_at.desc())
    )
    if only_open:
        stmt = stmt.where(ChatReport.handled.is_(False))

    rows = (await db.execute(stmt)).all()
    items = []
    for r, content, author_id, msg_deleted, author_name in rows:
        items.append({
            "id": r.id,
            "message_id": r.message_id,
            "reporter_id": r.reporter_id,
            "reason": r.reason,
            "handled": r.handled,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "message_content": content,
            "message_author_id": author_id,
            "message_author_name": author_name,
            "message_deleted": bool(msg_deleted),
        })
    return {"items": items, "count": len(items)}


@router.post("/chat/reports/{report_id}/dismiss")
async def dismiss_chat_report(
    report_id: int,
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a report as handled without touching the underlying message."""
    from models.portal.chat import ChatReport
    report = (
        await db.execute(select(ChatReport).where(ChatReport.id == report_id))
    ).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="report_not_found")
    report.handled = True
    db.add(report)
    await db.commit()
    return {"ok": True}


@router.delete("/chat/messages/{message_id}")
async def admin_delete_chat_message(
    message_id: int,
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete a chat message (admin override, no time limit) and
    mark every report pointing at it as handled in one pass.
    """
    from models.portal.chat import ChatMessage, ChatReport
    msg = (
        await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
    ).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="message_not_found")
    msg.deleted = True
    db.add(msg)
    # Auto-dismiss any pending reports on that message.
    await db.execute(
        ChatReport.__table__.update()
        .where(ChatReport.message_id == message_id, ChatReport.handled.is_(False))
        .values(handled=True)
    )
    await db.commit()
    return {"ok": True}
