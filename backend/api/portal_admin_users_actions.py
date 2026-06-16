"""Premium admin "Users" page — lifecycle / actions.
Routes mounted at ``/api/portal/admin/users`` (same prefix as the main
router). Covers: notes, tags, extend-access, Emby toggle, soft-delete,
restore, RGPD export, bulk runner, targeted notification, reset
password, force-logout, login history."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rate_limit import ip_key, limiter
from models.user import User
from api.auth import get_current_user, require_csrf

from api._portal_admin_users_helpers import (
    client_ip, client_ua, resolve_profile, rgpd_export_to_csv,
)
from services.portal.admin import update_user_quota as svc_update_quota
from services.portal.admin_users_activity import get_user_activity_summary
from services.portal.admin_users_actions import (
    extend_access as svc_extend_access,
    set_emby_account as svc_set_emby,
)
from services.portal.admin_users_lifecycle import (
    export_user_data_rgpd as svc_rgpd_export,
    restore_user as svc_restore,
    run_bulk_action as svc_bulk,
    set_admin_notes as svc_set_notes,
    set_tags as svc_set_tags,
    soft_delete_user as svc_soft_delete,
)
from services.portal.admin_users_notify import send_admin_notification
from services.portal.admin_users_security import (
    force_logout as svc_force_logout,
    list_user_login_history,
    reset_display_name as svc_reset_display_name,
    reset_local_password,
)

router = APIRouter(prefix="/api/portal/admin/users", tags=["portal-admin-users"])
logger = logging.getLogger("mediakeeper.api.portal_admin_users_actions")


class NotesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notes: str | None = Field(None, max_length=4000)


@router.patch("/{profile_id}/notes")
async def patch_notes(
    profile_id: int,
    data: NotesUpdate,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await svc_set_notes(
        db, profile, notes=data.notes, admin_user_id=admin.id,
        ip=client_ip(request), user_agent=client_ua(request),
    )


class TagsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tags: list[str] = Field(default_factory=list)


@router.patch("/{profile_id}/tags")
async def patch_tags(
    profile_id: int,
    data: TagsUpdate,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await svc_set_tags(
        db, profile, tags=data.tags or [], admin_user_id=admin.id,
        ip=client_ip(request), user_agent=client_ua(request),
    )


class QuotaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_allowed: int | None = Field(None, ge=1, le=100)
    unlimited: bool | None = None
    auto_approve: bool | None = None
    mode: str | None = Field(None, pattern="^(manual|auto)$")
    auto_min: int | None = Field(None, ge=1, le=100)
    auto_max: int | None = Field(None, ge=1, le=100)

    @model_validator(mode="after")
    def _ordered_bounds(self) -> "QuotaUpdate":
        if (
            self.auto_min is not None
            and self.auto_max is not None
            and self.auto_min > self.auto_max
        ):
            raise ValueError("auto_min must not exceed auto_max")
        return self


@router.patch("/{profile_id}/quota")
async def patch_quota(
    profile_id: int,
    data: QuotaUpdate,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    result = await svc_update_quota(
        db, profile.user_id, data.model_dump(exclude_none=True),
        admin_user_id=admin.id, ip=client_ip(request), user_agent=client_ua(request),
    )
    if result.get("error") == "invalid_bounds":
        raise HTTPException(status_code=422, detail="invalid_bounds")
    return result


class ExtendAccess(BaseModel):
    model_config = ConfigDict(extra="forbid")
    months: int = Field(..., ge=1, le=60)


@router.post("/{profile_id}/extend-access")
async def post_extend_access(
    profile_id: int,
    data: ExtendAccess,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await svc_extend_access(
        db, profile, months=data.months, admin_user_id=admin.id,
        ip=client_ip(request), user_agent=client_ua(request),
    )


class EmbyToggle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


@router.post("/{profile_id}/emby-toggle")
async def post_emby_toggle(
    profile_id: int,
    data: EmbyToggle,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await svc_set_emby(
        db, profile, enabled=data.enabled, admin_user_id=admin.id,
        ip=client_ip(request), user_agent=client_ua(request),
    )


@router.delete("/{profile_id}")
async def delete_soft(
    profile_id: int,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, user = await resolve_profile(profile_id, db)
    return await svc_soft_delete(
        db, profile, user, admin_user_id=admin.id,
        ip=client_ip(request), user_agent=client_ua(request),
    )


@router.post("/{profile_id}/restore")
async def post_restore(
    profile_id: int,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, user = await resolve_profile(profile_id, db)
    return await svc_restore(
        db, profile, user, admin_user_id=admin.id,
        ip=client_ip(request), user_agent=client_ua(request),
    )


@router.get("/{profile_id}/activity")
async def get_activity(
    profile_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await get_user_activity_summary(db, profile.user_id)


@router.get("/{profile_id}/export")
async def get_export(
    profile_id: int,
    request: Request,
    format: str = Query("json", pattern="^(json|csv)$"),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, user = await resolve_profile(profile_id, db)
    payload = await svc_rgpd_export(
        db, profile, user, admin_user_id=admin.id,
        ip=client_ip(request), user_agent=client_ua(request),
    )
    if format == "json":
        return payload
    return rgpd_export_to_csv(payload, profile_id)


class BulkAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(
        ..., pattern="^(activate|deactivate|delete|set_role|set_permissions|set_quota|export)$"
    )
    profile_ids: list[int] = Field(..., min_length=1, max_length=500)
    payload: dict | None = None


@router.post("/bulk")
async def post_bulk(
    data: BulkAction,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc_bulk(
        db,
        profile_ids=data.profile_ids,
        action=data.action,
        payload=data.payload,
        admin_user_id=admin.id,
        ip=client_ip(request),
        user_agent=client_ua(request),
    )


class NotifyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., min_length=1, max_length=120)
    body: str = Field(..., min_length=1, max_length=1000)


@router.post("/{profile_id}/notify")
async def post_notify(
    profile_id: int,
    data: NotifyPayload,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await send_admin_notification(
        db,
        target_user_id=profile.user_id,
        title=data.title,
        body=data.body,
        admin_user_id=admin.id,
        ip=client_ip(request),
        user_agent=client_ua(request),
    )


@router.post("/{profile_id}/reset-password")
@limiter.limit("3/minute", key_func=ip_key)
async def post_reset_password(
    profile_id: int,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, user = await resolve_profile(profile_id, db)
    return await reset_local_password(
        db, profile, user, admin_user_id=admin.id,
        ip=client_ip(request), user_agent=client_ua(request),
    )


@router.post("/{profile_id}/force-logout")
async def post_force_logout(
    profile_id: int,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await svc_force_logout(
        db, profile, admin_user_id=admin.id,
        ip=client_ip(request), user_agent=client_ua(request),
    )


@router.post("/{profile_id}/reset-display-name")
async def post_reset_display_name(
    profile_id: int,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await svc_reset_display_name(
        db, profile, admin_user_id=admin.id,
        ip=client_ip(request), user_agent=client_ua(request),
    )


@router.get("/{profile_id}/login-history")
async def get_login_history(
    profile_id: int,
    limit: int = Query(100, ge=1, le=500),
    cursor: str | None = Query(None),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await list_user_login_history(db, profile.user_id, limit=limit, cursor=cursor)
