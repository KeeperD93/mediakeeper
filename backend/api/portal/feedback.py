"""Portal feedback submission.

Delegated portal users (``can_report_feedback``) file a bug/suggestion that
lands in the admin moderation queue as ``pending``. An account with back-office
access runs that queue itself, so its reports relay straight to Discord, as from
the admin side (backend/api/feedback.py).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import require_permission
from constants.feedback import (
    ERR_INVALID_PLATFORM,
    ERR_INVALID_TYPE,
    ERR_NOT_CONFIGURED,
    ERR_SEND_FAILED,
    FEEDBACK_TYPES,
    MAX_DESCRIPTION,
    MAX_LOCATION,
    MAX_REPRODUCTION,
    MAX_RESOLUTION,
    MAX_TAGS,
    MAX_TITLE,
    PLATFORM_BOTH,
    TYPE_BUG,
)
from core.database import get_db
from core.rate_limit import limiter, portal_user_or_ip_key
from core.security import has_backoffice_access
from models.portal.profile import UserProfile
from models.user import User
from services.feedback import (
    PLATFORMS,
    create_pending_report,
    get_feedback_config,
    send_feedback_report,
)

router = APIRouter(prefix="/feedback", tags=["portal-feedback"])


class PortalFeedbackReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = TYPE_BUG
    title: str = Field(min_length=1, max_length=MAX_TITLE)
    description: str = Field(min_length=1, max_length=MAX_DESCRIPTION)
    reproduction: str = Field(default="", max_length=MAX_REPRODUCTION)
    zone: str = Field(default="", max_length=MAX_LOCATION)
    module: str = Field(default="", max_length=MAX_LOCATION)
    tab: str = Field(default="", max_length=MAX_LOCATION)
    platform: str = PLATFORM_BOTH
    resolution: str = Field(default="", max_length=MAX_RESOLUTION)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    anonymous: bool = False


@router.post("")
@limiter.limit("5/minute", key_func=portal_user_or_ip_key)
async def submit_portal_feedback(
    req: PortalFeedbackReport,
    request: Request,
    up: tuple[User, UserProfile] = Depends(require_permission("can_report_feedback")),
    db: AsyncSession = Depends(get_db),
):
    cfg = await get_feedback_config(db)
    if not cfg["enabled"] or not cfg["webhook_url"]:
        raise HTTPException(status_code=400, detail=ERR_NOT_CONFIGURED)
    if req.platform not in PLATFORMS:
        raise HTTPException(status_code=422, detail=ERR_INVALID_PLATFORM)
    if req.type not in FEEDBACK_TYPES:
        raise HTTPException(status_code=422, detail=ERR_INVALID_TYPE)
    user, profile = up
    fields = req.model_dump()
    if has_backoffice_access(user.username, user.hashed_password, is_active=user.is_active):
        # A failed relay is reported, never queued: the admin would only be
        # asked to approve their own report.
        if not await send_feedback_report(db, fields):
            raise HTTPException(status_code=502, detail=ERR_SEND_FAILED)
        return {"ok": True}
    await create_pending_report(
        db,
        reporter_user_id=user.id,
        reporter_name=profile.display_name,
        fields=fields,
    )
    return {"ok": True}
