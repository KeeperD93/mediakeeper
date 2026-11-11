"""Portal maintenance-mode endpoints.

Two surfaces:

* ``GET /api/portal/maintenance`` — anonymous, locale-aware. The SPA
  needs the maintenance state *before* the user logs in (otherwise a
  fresh visitor reaches the login screen instead of the holding page).
  Rate-limited via slowapi's IP key.

* ``GET /api/portal/admin/maintenance`` and ``PATCH`` of the same —
  admin-only, return / update the full FR + EN texts plus the flag.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rate_limit import ip_key, limiter
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_request_lang, require_admin
from services.portal import maintenance as maintenance_svc

router = APIRouter(tags=["portal-maintenance"])


# ---------------------------------------------------------------------------
# Public endpoint — anonymous access required (the SPA router guard hits
# it on every navigation, including the unauthenticated landing).
# ---------------------------------------------------------------------------

@router.get("/maintenance")
@limiter.limit("120/minute", key_func=ip_key)
async def get_maintenance(
    request: Request,
    lang: str = Depends(get_request_lang),
    db: AsyncSession = Depends(get_db),
):
    """Anonymous read: ``{enabled, text}`` resolved for the client locale."""
    return await maintenance_svc.get_maintenance_state(db, lang)


# ---------------------------------------------------------------------------
# Admin surface — full FR + EN text + flag, read/write.
# ---------------------------------------------------------------------------

class MaintenanceAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    text_fr: str | None = Field(None, max_length=2000)
    text_en: str | None = Field(None, max_length=2000)


@router.get("/admin/maintenance")
async def get_maintenance_admin(
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await maintenance_svc.get_maintenance_admin_settings(db)


@router.patch("/admin/maintenance")
async def update_maintenance_admin(
    payload: MaintenanceAdminUpdate,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await maintenance_svc.update_maintenance_settings(
        db,
        enabled=payload.enabled,
        text_fr=payload.text_fr,
        text_en=payload.text_en,
    )
