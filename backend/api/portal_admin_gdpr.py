"""Admin endpoints for the GDPR opt-in settings.

Two surfaces:

* ``GET  /api/portal/admin/gdpr/settings`` — returns every ``gdpr.*``
  value at once so the admin form can prefill.
* ``PUT  /api/portal/admin/gdpr/settings`` — partial update, only the
  fields the client sent. ``privacy_text_fr`` / ``privacy_text_en``
  pass through ``sanitize_html`` before persistence so the canonical
  safety boundary (Tiptap → bleach pipeline reused from the Help
  Center) is never bypassed by direct admin writes.

The pending-deletion list and the per-user cancel live in
``portal_admin_users.py`` (filter ``?pending_deletion=true``) and
``portal_admin_users_gdpr.py`` (admin-side cancel), wired in Batch
11B Phase 1.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from api.auth import get_current_user, require_csrf
from core.database import get_db
from models.user import User
from services.portal._html_sanitize import sanitize_html
from services.portal.gdpr import (
    DELAY_MAX_DAYS,
    DELAY_MIN_DAYS,
    GDPR_DELAY_KEY,
    GDPR_DPO_KEY,
    GDPR_ENABLED_KEY,
    GDPR_PRIVACY_EN_KEY,
    GDPR_PRIVACY_FR_KEY,
    get_purge_delay_days,
    is_gdpr_enabled,
    refresh_pending_grace,
)
from services.settings import get_settings_map, set_settings_map


router = APIRouter(prefix="/api/portal/admin/gdpr", tags=["portal-admin-gdpr"])
logger = logging.getLogger("mediakeeper.api.portal_admin_gdpr")


def _parse_bool(raw: str | None) -> bool:
    if not raw:
        return False
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _parse_delay(raw: str | None) -> int:
    if not raw:
        return 30
    try:
        n = int(raw)
    except (ValueError, TypeError):
        return 30
    return max(DELAY_MIN_DAYS, min(DELAY_MAX_DAYS, n))


_ALL_KEYS = (
    GDPR_ENABLED_KEY,
    GDPR_PRIVACY_FR_KEY,
    GDPR_PRIVACY_EN_KEY,
    GDPR_DPO_KEY,
    GDPR_DELAY_KEY,
)


class GdprSettingsUpdate(BaseModel):
    # Forbid unknown keys: a stale frontend or a probe must not be
    # able to slip an arbitrary setting through this pathway.
    model_config = ConfigDict(extra="forbid")

    enabled: Optional[bool] = None
    privacy_text_fr: Optional[str] = None
    privacy_text_en: Optional[str] = None
    dpo_contact: Optional[str] = Field(None, max_length=300)
    account_purge_delay_days: Optional[int] = Field(
        None, ge=DELAY_MIN_DAYS, le=DELAY_MAX_DAYS,
    )


@router.get("/settings")
async def get_gdpr_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return the current GDPR setting values for the admin form."""
    raw = await get_settings_map(db, list(_ALL_KEYS))
    return {
        "enabled": _parse_bool(raw.get(GDPR_ENABLED_KEY)),
        "privacy_text_fr": raw.get(GDPR_PRIVACY_FR_KEY) or "",
        "privacy_text_en": raw.get(GDPR_PRIVACY_EN_KEY) or "",
        "dpo_contact": raw.get(GDPR_DPO_KEY) or "",
        "account_purge_delay_days": _parse_delay(raw.get(GDPR_DELAY_KEY)),
    }


@router.put("/settings")
async def put_gdpr_settings(
    payload: GdprSettingsUpdate,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partial update of the ``gdpr.*`` settings.

    Only the fields the client sent are persisted; the rest stay
    untouched. HTML privacy texts pass through ``sanitize_html`` so
    the safety boundary cannot be skipped by sending raw HTML.
    """
    sent = payload.model_fields_set
    updates: dict[str, str] = {}
    # Detect a disabled -> enabled transition (read the live value before the
    # write) so frozen deletion requests get a fresh grace window instead of
    # being purged instantly on the next run.
    gdpr_reenabled = "enabled" in sent and payload.enabled and not await is_gdpr_enabled(db)
    if "enabled" in sent:
        updates[GDPR_ENABLED_KEY] = "true" if payload.enabled else "false"
    if "privacy_text_fr" in sent:
        updates[GDPR_PRIVACY_FR_KEY] = sanitize_html(payload.privacy_text_fr or "")
    if "privacy_text_en" in sent:
        updates[GDPR_PRIVACY_EN_KEY] = sanitize_html(payload.privacy_text_en or "")
    if "dpo_contact" in sent:
        updates[GDPR_DPO_KEY] = (payload.dpo_contact or "").strip()
    if "account_purge_delay_days" in sent:
        # Range already enforced by Pydantic; persist as string for the
        # generic key/value table.
        updates[GDPR_DELAY_KEY] = str(int(payload.account_purge_delay_days or 30))

    if updates:
        await set_settings_map(db, updates)
        logger.info(
            "[GDPR_SETTINGS] admin_user_id=%s updated keys=%s",
            admin.id, sorted(updates.keys()),
        )

    if gdpr_reenabled:
        await refresh_pending_grace(db, delay_days=await get_purge_delay_days(db))

    raw = await get_settings_map(db, list(_ALL_KEYS))
    return {
        "enabled": _parse_bool(raw.get(GDPR_ENABLED_KEY)),
        "privacy_text_fr": raw.get(GDPR_PRIVACY_FR_KEY) or "",
        "privacy_text_en": raw.get(GDPR_PRIVACY_EN_KEY) or "",
        "dpo_contact": raw.get(GDPR_DPO_KEY) or "",
        "account_purge_delay_days": _parse_delay(raw.get(GDPR_DELAY_KEY)),
    }
