"""Portal feedback submission.

Delegated portal users (``can_report_feedback``) file a bug/suggestion that
lands in the admin moderation queue as ``pending``. The admin-gated direct relay
lives in backend/api/feedback.py; this route never sends to Discord itself.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rate_limit import limiter, portal_user_or_ip_key
from api.portal.deps import require_permission
from models.portal.profile import UserProfile
from models.user import User
from services.feedback import PLATFORMS, create_pending_report, get_feedback_config

router = APIRouter(prefix="/feedback", tags=["portal-feedback"])


class PortalFeedbackReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = "bug"
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1500)
    reproduction: str = Field(default="", max_length=500)
    zone: str = Field(default="", max_length=120)
    module: str = Field(default="", max_length=120)
    tab: str = Field(default="", max_length=120)
    platform: str = "both"
    resolution: str = Field(default="", max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=12)
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
        raise HTTPException(status_code=400, detail="not_configured")
    if req.platform not in PLATFORMS:
        raise HTTPException(status_code=422, detail="invalid_platform")
    user, profile = up
    await create_pending_report(
        db,
        reporter_user_id=user.id,
        reporter_name=profile.display_name,
        fields=req.model_dump(),
    )
    return {"ok": True}
