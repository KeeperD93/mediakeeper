"""Requests admin session: auto-provisioned profile + rq_token issuance."""
import logging
from datetime import datetime, timezone

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token
from models.portal.profile import UserProfile
from models.user import User
from services.portal.admin import get_portal_flag
from services.portal.admin_users_constants import ROLE_ADMIN
from services.portal.news import get_unread_news

from ._cookies import _set_portal_jwt_cookie

logger = logging.getLogger("mediakeeper.api.auth")


async def _serialize_portal_ui_flags(
    db: AsyncSession,
    profile: UserProfile,
) -> dict:
    is_admin = profile.role == ROLE_ADMIN
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


async def _stamp_login(
    db: AsyncSession,
    user_id: int,
    *,
    client_ip: str,
    user_agent: str | None,
) -> None:
    """Stamp the UserProfile with this sign-in, admin or member, so the admin
    "Users" page shows a real last sign-in (otherwise the profile only sees /me
    pings). Takes an id, not the account: a commit that fails in its flush
    expires every loaded object, which the failure log could not read back.
    Best effort: a failure is logged and rolled back, the sign-in goes on."""
    try:
        profile = (
            await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
        ).scalar_one_or_none()
        if not profile:
            return
        now = datetime.now(timezone.utc)
        profile.last_login_at = now
        profile.last_seen_at = now
        profile.last_login_ip = client_ip
        profile.last_login_user_agent = (user_agent or "")[:255] or None
        db.add(profile)
        await db.commit()
    except Exception:
        logger.exception("[LOGIN] Profile stamp failed for user_id=%s", user_id)
        await db.rollback()


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
            role=ROLE_ADMIN,
            account_active=True,
            source="local",
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile

    touched = False
    if profile.role != ROLE_ADMIN:
        profile.role = ROLE_ADMIN
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
