"""Premium admin "Users" page — list / detail / identity / role / permissions.

Mounted at ``/api/portal/admin/users``. Auth = ``mk_token`` cookie via
``get_current_user`` (backoffice admin only — same surface as the
existing ``portal_admin_requests`` router).

Companion routers (kept short to honour the 300-line cap):

- ``portal_admin_users_actions`` — access window, Emby toggle, soft-delete,
  RGPD export, bulk runner, targeted notification, notes, tags.
- ``portal_admin_users_emby``    — selective Emby import + manual local
  account creation.
"""
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from api.auth import get_current_user, require_csrf

from api._portal_admin_users_helpers import client_ip, client_ua, resolve_profile
from services.portal.admin_users import (
    get_admin_user_detail,
    list_admin_users,
    update_user_identity as svc_update_identity,
)
from services.portal.admin_users_actions import (
    set_access_window as svc_set_access,
    set_account_active as svc_set_active,
    update_permissions as svc_update_perms,
    update_role as svc_update_role,
)
from services.portal.admin_users_audit import list_audit_for_user
from services.portal.admin_users_constants import (
    PERMISSION_KEYS,
    ROLE_PRESETS,
    ROLES,
    SOURCES,
)

router = APIRouter(prefix="/api/portal/admin/users", tags=["portal-admin-users"])
logger = logging.getLogger("mediakeeper.api.portal_admin_users")


@router.get("/role-presets")
async def role_presets(_: User = Depends(get_current_user)):
    """Return the role → permissions preset map so the frontend doesn't
    have to mirror it."""
    return {
        "roles": list(ROLES),
        "sources": list(SOURCES),
        "permissions": list(PERMISSION_KEYS),
        "presets": ROLE_PRESETS,
    }


@router.get("")
async def list_users(
    search: Optional[str] = Query(None, max_length=100),
    source: Optional[str] = Query(None, pattern="^(emby|local)$"),
    role: Optional[str] = Query(None, pattern="^(viewer|moderator|admin)$"),
    status: Optional[str] = Query(None, pattern="^(active|inactive|expired|never_logged_in)$"),
    expires_within: Optional[int] = Query(None, ge=1, le=365),
    include_deleted: bool = Query(False),
    tag: Optional[str] = Query(None, max_length=32),
    pending_deletion: Optional[bool] = Query(None),
    sort: str = Query("display_name"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_admin_users(
        db,
        search=search,
        source=source,
        role=role,
        status=status,
        expires_within=expires_within,
        include_deleted=include_deleted,
        tag=tag,
        pending_deletion=pending_deletion,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )


@router.get("/stats")
async def get_stats(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.portal.admin_users_stats import get_users_stats
    return await get_users_stats(db)


@router.get("/tags")
async def get_tags(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.portal.admin_users_stats import list_distinct_tags
    return await list_distinct_tags(db)


@router.get("/{profile_id}")
async def get_user(
    profile_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    detail = await get_admin_user_detail(db, profile_id)
    if not detail:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return detail


@router.get("/{profile_id}/audit")
async def get_user_audit(
    profile_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await list_audit_for_user(db, profile.user_id, limit=limit, offset=offset)


class IdentityUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=50)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)


@router.patch("/{profile_id}")
async def patch_identity(
    profile_id: int,
    data: IdentityUpdate,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, user = await resolve_profile(profile_id, db)
    result = await svc_update_identity(
        db,
        profile,
        user,
        display_name=data.display_name,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        admin_user_id=admin.id,
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    # Surface the anti-empty guard as a real HTTP 400 — the form needs a
    # hard failure to trigger the error toast and keep the cleared field.
    if isinstance(result, dict) and result.get("error") == "display_name_empty":
        raise HTTPException(status_code=400, detail="display_name_empty")
    return result


class RoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(viewer|moderator|admin)$")


@router.patch("/{profile_id}/role")
async def patch_role(
    profile_id: int,
    data: RoleUpdate,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await svc_update_role(
        db,
        profile,
        role=data.role,
        admin_user_id=admin.id,
        ip=client_ip(request),
        user_agent=client_ua(request),
    )


class PermissionsUpdate(BaseModel):
    permissions: dict[str, bool]


@router.patch("/{profile_id}/permissions")
async def patch_permissions(
    profile_id: int,
    data: PermissionsUpdate,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await svc_update_perms(
        db,
        profile,
        permissions=data.permissions,
        admin_user_id=admin.id,
        ip=client_ip(request),
        user_agent=client_ua(request),
    )


class ActiveUpdate(BaseModel):
    active: bool


@router.patch("/{profile_id}/active")
async def patch_active(
    profile_id: int,
    data: ActiveUpdate,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, user = await resolve_profile(profile_id, db)
    return await svc_set_active(
        db,
        profile,
        user,
        active=data.active,
        admin_user_id=admin.id,
        ip=client_ip(request),
        user_agent=client_ua(request),
    )


class AccessWindow(BaseModel):
    start: Optional[datetime] = None
    end: Optional[datetime] = None


@router.patch("/{profile_id}/access")
async def patch_access(
    profile_id: int,
    data: AccessWindow,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await svc_set_access(
        db,
        profile,
        start=data.start,
        end=data.end,
        admin_user_id=admin.id,
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
