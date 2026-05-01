"""Per-user activity feeds — trophies, XP ledger, requests, problems.

Mounted at ``/api/portal/admin/users``. Read-only, admin-gated. Each
endpoint resolves the profile id then proxies to the matching feed
helper in ``services.portal.admin_users_feed``.
"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from api.auth import get_current_user

from api._portal_admin_users_helpers import resolve_profile
from services.portal.admin_users_feed import (
    list_user_requests,
    list_user_tickets,
    list_user_trophies,
    list_user_xp_ledger,
)

router = APIRouter(prefix="/api/portal/admin/users", tags=["portal-admin-users"])
logger = logging.getLogger("mediakeeper.api.portal_admin_users_feed")


@router.get("/{profile_id}/trophies")
async def get_trophies(
    profile_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await list_user_trophies(db, profile.user_id)


@router.get("/{profile_id}/xp-history")
async def get_xp_history(
    profile_id: int,
    limit: int = Query(100, ge=1, le=500),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await list_user_xp_ledger(db, profile.user_id, limit=limit)


@router.get("/{profile_id}/requests")
async def get_requests(
    profile_id: int,
    limit: int = Query(100, ge=1, le=500),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await list_user_requests(db, profile.user_id, limit=limit)


@router.get("/{profile_id}/tickets")
async def get_tickets(
    profile_id: int,
    limit: int = Query(100, ge=1, le=500),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _user = await resolve_profile(profile_id, db)
    return await list_user_tickets(db, profile.user_id, limit=limit)
