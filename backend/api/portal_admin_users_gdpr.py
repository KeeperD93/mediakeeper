"""Admin endpoints for the GDPR opt-in mode (Batch 11B).

Two surfaces:

* ``DELETE /api/portal/admin/users/{profile_id}/deletion-request`` —
  admin-side cancel of a user's pending deletion request, used when a
  user contacts support directly. Writes an audit row.

The list of users currently in the grace period is exposed by adding a
``pending_deletion`` boolean filter to the existing
``GET /api/portal/admin/users`` endpoint (see ``portal_admin_users.py``).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api._portal_admin_users_helpers import client_ip, client_ua, resolve_profile
from api.auth import get_current_user, require_csrf
from core.database import get_db
from models.user import User
from services.portal.gdpr import admin_cancel_deletion_request


router = APIRouter(prefix="/api/portal/admin/users", tags=["portal-admin-users"])
logger = logging.getLogger("mediakeeper.api.portal_admin_users_gdpr")


@router.delete("/{profile_id}/deletion-request")
async def admin_delete_deletion_request(
    profile_id: int,
    request: Request,
    _csrf: None = Depends(require_csrf),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin-side cancel: clears ``deletion_requested_at`` and
    ``pending_deletion_at`` on the target user. Does not touch tokens
    (the user kept logging in normally during the grace period).

    404 if the user has no pending request.
    """
    _profile, user = await resolve_profile(profile_id, db)
    result = await admin_cancel_deletion_request(
        db, user,
        admin_user_id=admin.id,
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    if result.get("error") == "no_pending_request":
        raise HTTPException(status_code=404, detail="no_pending_request")
    return result
