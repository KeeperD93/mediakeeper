"""Bug/suggestion feedback endpoints (Cycle 1: admin config + direct relay).

The report is relayed to a maintainer-provided Discord webhook. Admin-gated and
rate-limited; CSRF is enforced globally by ``CsrfMiddleware`` on every mutation.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from core.rate_limit import admin_user_or_ip_key, limiter
from core.url_safety import is_discord_webhook_url
from models.user import User
from services.feedback import (
    PLATFORMS,
    get_feedback_config,
    list_feedback_reports,
    reject_feedback_report,
    save_feedback_config,
    send_feedback_handshake,
    send_feedback_report,
    update_feedback_report,
    validate_feedback_report,
)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool | None = None
    discord_pseudo: str | None = Field(default=None, max_length=100)
    webhook_url: str | None = Field(default=None, max_length=500)


class FeedbackReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = "bug"
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1500)
    reproduction: str = Field(default="", max_length=500)
    zone: str = Field(default="", max_length=100)
    module: str = Field(default="", max_length=100)
    tab: str = Field(default="", max_length=100)
    platform: str = "both"
    resolution: str = Field(default="", max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=12)
    anonymous: bool = False


class FeedbackReportUpdate(BaseModel):
    """Admin edits to a pending report before validation — every field optional."""
    model_config = ConfigDict(extra="forbid")
    type: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=1500)
    reproduction: str | None = Field(default=None, max_length=500)
    zone: str | None = Field(default=None, max_length=100)
    module: str | None = Field(default=None, max_length=100)
    tab: str | None = Field(default=None, max_length=100)
    platform: str | None = None
    resolution: str | None = Field(default=None, max_length=40)
    tags: list[str] | None = Field(default=None, max_length=12)


_VALIDATE_ERRORS = {"not_found": 404, "not_configured": 400, "send_failed": 502}


def _public_config(cfg: dict) -> dict:
    """Shape returned to the browser — the stored webhook URL never leaves."""
    return {
        "enabled": cfg["enabled"],
        "discord_pseudo": cfg["discord_pseudo"],
        "webhook_configured": bool(cfg["webhook_url"]),
    }


@router.get("/config")
async def read_config(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _public_config(await get_feedback_config(db))


@router.post("/config")
async def write_config(
    req: FeedbackConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if req.webhook_url and not is_discord_webhook_url(req.webhook_url):
        raise HTTPException(status_code=422, detail="invalid_webhook")
    await save_feedback_config(
        db,
        enabled=req.enabled,
        discord_pseudo=req.discord_pseudo,
        webhook_url=req.webhook_url,
    )
    return _public_config(await get_feedback_config(db))


@router.post("/test")
@limiter.limit("5/minute", key_func=admin_user_or_ip_key)
async def test_link(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cfg = await get_feedback_config(db)
    if not cfg["webhook_url"]:
        raise HTTPException(status_code=400, detail="not_configured")
    if not await send_feedback_handshake(cfg["webhook_url"]):
        raise HTTPException(status_code=502, detail="send_failed")
    return {"ok": True}


@router.post("")
@limiter.limit("5/minute", key_func=admin_user_or_ip_key)
async def submit_report(
    req: FeedbackReport,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cfg = await get_feedback_config(db)
    if not cfg["enabled"] or not cfg["webhook_url"]:
        raise HTTPException(status_code=400, detail="not_configured")
    if req.platform not in PLATFORMS:
        raise HTTPException(status_code=422, detail="invalid_platform")
    if not await send_feedback_report(db, req.model_dump()):
        raise HTTPException(status_code=502, detail="send_failed")
    return {"ok": True}


@router.get("/reports")
async def list_reports(
    status: str = "pending",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Moderation queue: pending reports awaiting review, or the rejected bin."""
    if status not in ("pending", "rejected"):
        raise HTTPException(status_code=422, detail="invalid_status")
    return {"items": await list_feedback_reports(db, status)}


@router.patch("/reports/{report_id}")
async def edit_report(
    report_id: int,
    req: FeedbackReportUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    updates = req.model_dump(exclude_unset=True)
    if "platform" in updates and updates["platform"] not in PLATFORMS:
        raise HTTPException(status_code=422, detail="invalid_platform")
    # title/description/type are NOT NULL: an explicit JSON null passes the
    # str|None schema but would 500 on the UPDATE — reject it at the boundary.
    for key in ("title", "description", "type"):
        if key in updates and updates[key] is None:
            raise HTTPException(status_code=422, detail="invalid_" + key)
    if not await update_feedback_report(db, report_id, updates):
        raise HTTPException(status_code=404, detail="not_found")
    return {"ok": True}


@router.post("/reports/{report_id}/validate")
@limiter.limit("10/minute", key_func=admin_user_or_ip_key)
async def validate_report(
    report_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Relay a pending report to Discord, then drop it from the queue."""
    result = await validate_feedback_report(db, report_id)
    if result != "sent":
        raise HTTPException(status_code=_VALIDATE_ERRORS[result], detail=result)
    return {"ok": True}


@router.post("/reports/{report_id}/reject")
async def reject_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Reject a pending report — kept 30 days (purge is Cycle 3c), then gone."""
    if not await reject_feedback_report(db, report_id):
        raise HTTPException(status_code=404, detail="not_found")
    return {"ok": True}
