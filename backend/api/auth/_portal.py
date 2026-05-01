"""Requests admin session: auto-provisioned profile + rq_token issuance."""
import logging

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token
from models.portal.profile import UserProfile
from models.user import User
from services.portal.admin import get_portal_flag
from services.portal.news import get_unread_news

from ._cookies import _set_portal_jwt_cookie

logger = logging.getLogger("mediakeeper.api.auth")


async def _serialize_portal_ui_flags(
    db: AsyncSession,
    profile: UserProfile,
) -> dict:
    is_admin = profile.role == "admin"
    anonymize_requests = False if is_admin else await get_portal_flag(
        db,
        "portal.anonymize_requests",
    )
    return {
        "show_requests_tab": is_admin or not anonymize_requests,
    }


async def _safe_serialize_portal_ui_flags(
    db: AsyncSession,
    profile: UserProfile,
) -> dict:
    try:
        return await _serialize_portal_ui_flags(db, profile)
    except Exception as exc:
        logger.warning(
            "[PORTAL_LOGIN] UI flags fallback for user_id=%s: %s",
            getattr(profile, "user_id", "unknown"),
            exc,
        )
        return {"show_requests_tab": True}


async def _safe_get_unread_news_count(db: AsyncSession, user_id: int) -> int:
    try:
        unread = await get_unread_news(db, user_id)
        return len(unread)
    except Exception as exc:
        logger.warning(
            "[PORTAL_LOGIN] unread news fallback for user_id=%s: %s",
            user_id,
            exc,
        )
        return 0


async def ensure_portal_admin_profile(
    current: User,
    db: AsyncSession,
) -> UserProfile:
    """Create/upgrade the Requests profile for a backoffice admin."""
    profile = (
        await db.execute(
            select(UserProfile).where(UserProfile.user_id == current.id)
        )
    ).scalar_one_or_none()

    if not profile:
        profile = UserProfile(
            user_id=current.id,
            display_name=current.username,
            role="admin",
            account_active=True,
            source="local",
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile

    touched = False
    if profile.role != "admin":
        profile.role = "admin"
        touched = True
    if not profile.account_active:
        profile.account_active = True
        touched = True
    if not profile.source and not profile.emby_user_id:
        profile.source = "local"
        touched = True

    if touched:
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return profile


async def grant_portal_admin_session(
    request: Request,
    response: Response,
    current: User,
    db: AsyncSession,
) -> UserProfile:
    """Provision the admin Requests profile and issue the rq_token cookie."""
    profile = await ensure_portal_admin_profile(current, db)
    token = create_access_token({"sub": current.username, "scope": "portal"})
    _set_portal_jwt_cookie(response, token, request)
    return profile
