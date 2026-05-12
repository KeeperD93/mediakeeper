"""Portal admin endpoints: user management, stats, index sync."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.auth import get_current_user
from api.portal.deps import require_admin
from services.portal import admin as admin_svc
from services.portal import admin_engagement as engagement_svc
from services.portal import chat as chat_svc
from services.portal import mk_events as mk_events_svc
from services.portal.emby_index import sync_emby_tmdb_index

router = APIRouter(prefix="/admin", tags=["portal-admin"])


class RoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(admin|viewer)$")


class ActiveUpdate(BaseModel):
    active: bool


class QuotaUpdate(BaseModel):
    max_allowed: Optional[int] = Field(None, ge=1, le=100)
    unlimited: Optional[bool] = None
    auto_approve: Optional[bool] = None
    mode: Optional[str] = Field(None, pattern="^(fixed|proportional)$")


class MuteUser(BaseModel):
    muted_until: datetime
    reason: Optional[str] = Field(None, max_length=300)


@router.get("/stats")
async def admin_stats(
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_svc.get_admin_stats(db)


@router.get("/engagement")
async def admin_engagement(
    window: int = Query(1, description="Window in days, 1 or 7"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Engagement counters (lists, trophies, chat, reviews, signups) over 1 or 7 days."""
    return await engagement_svc.get_admin_engagement(db, window_days=window)


@router.get("/events/upcoming")
async def admin_events_upcoming(
    limit: int = Query(5, ge=1, le=20),
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Next scheduled events portal-wide, regardless of privacy (admin view)."""
    return {"items": await mk_events_svc.list_upcoming_admin(db, limit=limit)}


@router.put("/users/{user_id}/role")
async def set_role(
    user_id: int,
    data: RoleUpdate,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await admin_svc.update_user_role(db, user_id, data.role)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.put("/users/{user_id}/active")
async def set_active(
    user_id: int,
    data: ActiveUpdate,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await admin_svc.toggle_user_active(db, user_id, data.active)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.put("/users/{user_id}/quota")
async def set_quota(
    user_id: int,
    data: QuotaUpdate,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await admin_svc.update_user_quota(db, user_id, data.model_dump(exclude_none=True))
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.put("/users/{user_id}/chat")
async def toggle_chat(
    user_id: int,
    enabled: bool = Query(...),
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await admin_svc.toggle_chat(db, user_id, enabled)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/users/{user_id}/mute")
async def mute_user(
    user_id: int,
    data: MuteUser,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await chat_svc.mute_user(db, user_id, data.muted_until, data.reason)


@router.post("/users/{user_id}/unmute")
async def unmute_user(
    user_id: int,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await chat_svc.unmute_user(db, user_id)


@router.put("/users/{user_id}/force-public")
async def force_public(
    user_id: int,
    forced: Optional[bool] = Query(None),
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await admin_svc.force_public_profile(db, user_id, forced)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/sync-index")
async def sync_index(
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Trigger Emby ↔ TMDB index sync."""
    return await sync_emby_tmdb_index(db)


# ---------------------------------------------------------------------------
# Portal-wide settings (flags). Exposed to admins only.
# ---------------------------------------------------------------------------

class PortalSettingsUpdate(BaseModel):
    # Strict mode: any unknown key (e.g. a frontend typo or a stale field
    # left over after a backend rename) surfaces as 422 instead of being
    # silently dropped. Forward-compatibility for older frontends is
    # already covered by every flag being Optional with a None default,
    # so a backend-side addition does not require a synchronous frontend
    # update.
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    anonymize_requests: Optional[bool] = None
    hero_trend_count: Optional[int] = None
    # Dotted JSON key (``requests.auto_cleanup_days``) preserved via
    # alias so the frontend can address the setting under its real
    # ``requests.`` namespace instead of being lifted into the
    # ``portal.`` one.
    requests_auto_cleanup_days: Optional[int] = Field(
        default=None,
        ge=0,
        le=365,
        alias="requests.auto_cleanup_days",
    )


@router.get("/settings")
async def get_settings(
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Return all Portal-wide admin flags (anonymize_requests, ...).
    Keys come back without the ``portal.`` prefix so the frontend form
    can bind directly. Keys from other namespaces (e.g.
    ``requests.auto_cleanup_days``) are passed through unchanged.
    """
    raw = await admin_svc.get_portal_settings(db)
    return {k.replace("portal.", ""): v for k, v in raw.items()}


@router.patch("/settings")
async def patch_settings(
    payload: PortalSettingsUpdate,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update one or more Portal-wide admin settings."""
    updates: dict = {}
    if payload.anonymize_requests is not None:
        updates["portal.anonymize_requests"] = payload.anonymize_requests
    if payload.hero_trend_count is not None:
        updates["portal.hero_trend_count"] = payload.hero_trend_count
    if payload.requests_auto_cleanup_days is not None:
        updates["requests.auto_cleanup_days"] = payload.requests_auto_cleanup_days
    raw = await admin_svc.update_portal_settings(db, updates)
    return {k.replace("portal.", ""): v for k, v in raw.items()}
