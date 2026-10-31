"""Portal session: the signed-in member (/me) and sign-out (/logout).

Signing in goes through /api/auth/portal-login.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_access_token
from api.auth import PORTAL_COOKIE_NAME
from api.auth._csrf import ensure_csrf_cookie
from api.portal.deps import get_current_profile
from models.user import User
from models.portal.profile import UserProfile
from services.portal.profiles import serialize_profile_with_effective_lang
from services.portal.news import get_unread_news
from services.feedback import get_feedback_config
from services.portal.admin import get_donation_config, get_portal_flag
from services.portal.admin_users_constants import ROLE_ADMIN

logger = logging.getLogger("mediakeeper.portal.auth")
router = APIRouter(prefix="/auth", tags=["portal-auth"])


async def _serialize_ui_flags(db: AsyncSession, profile: UserProfile) -> dict:
    is_admin = profile.role == ROLE_ADMIN
    anonymize_requests = False if is_admin else await get_portal_flag(
        db,
        "portal.anonymize_requests",
    )
    allow_adult_requests = is_admin or await get_portal_flag(
        db,
        "portal.allow_adult_requests",
    )
    feedback = await get_feedback_config(db)
    return {
        "show_requests_tab": is_admin or not anonymize_requests,
        "allow_adult_requests": allow_adult_requests,
        "donation": await get_donation_config(db),
        "feedback_enabled": bool(feedback["enabled"] and feedback["webhook_url"]),
        "can_report": is_admin or bool(profile.can_report_feedback),
    }


async def _safe_serialize_ui_flags(db: AsyncSession, profile: UserProfile) -> dict:
    try:
        return await _serialize_ui_flags(db, profile)
    except Exception as exc:
        logger.warning(
            "[PORTAL_AUTH] UI flags fallback for user_id=%s: %s",
            profile.user_id, exc,
        )
        # Mirror the full success shape so the frontend never reads an absent
        # flag on the degraded path (fail-closed: the request button stays
        # disabled rather than wrongly enabled).
        return {
            "show_requests_tab": True,
            "allow_adult_requests": False,
            "donation": {"enabled": False, "url": "", "message": "", "button_label": ""},
            "feedback_enabled": False,
            "can_report": False,
        }


async def _safe_get_unread_news(db: AsyncSession, user_id: int) -> list[dict]:
    try:
        return await get_unread_news(db, user_id)
    except Exception as exc:
        logger.warning(
            "[PORTAL_AUTH] unread news fallback for user_id=%s: %s", user_id, exc,
        )
        return []


@router.get("/me")
async def portal_me(
    request: Request,
    response: Response,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Get current portal user info."""
    ensure_csrf_cookie(response, request)
    user, profile = up

    # Bump last_seen_at so the admin "Users" page can drive its online
    # indicator. We only re-write when the previous bump is older than
    # 30s to avoid hammering the DB on a noisy /me poll.
    try:
        now = datetime.now(timezone.utc)
        previous = profile.last_seen_at
        if previous is None or previous.tzinfo is None or (now - previous) > timedelta(seconds=30):
            profile.last_seen_at = now
            db.add(profile)
            await db.commit()
    except Exception as exc:
        logger.warning(
            "[PORTAL_ME] last_seen bump failed for user_id=%s: %s", user.id, exc,
        )
        await db.rollback()

    unread = await _safe_get_unread_news(db, user.id)
    return {
        "profile": await serialize_profile_with_effective_lang(db, profile, user=user),
        "unread_news_count": len(unread),
        "ui": await _safe_serialize_ui_flags(db, profile),
        "gdpr": await _safe_serialize_gdpr(db, user),
    }


async def _safe_serialize_gdpr(db: AsyncSession, user: User) -> dict:
    """Expose the toggle + this user's pending deletion timestamp.

    The UI uses ``enabled`` to decide whether to show the Privacy tab,
    and ``pending_deletion_at`` to render the grace-period banner. A DB
    hiccup must not break ``/me`` — fall back to the disabling defaults.
    """
    try:
        from services.portal.gdpr import is_gdpr_enabled
        enabled = await is_gdpr_enabled(db)
    except Exception as exc:
        logger.warning(
            "[PORTAL_AUTH] GDPR flags fallback for user_id=%s: %s", user.id, exc,
        )
        enabled = False
    pending = user.pending_deletion_at
    requested = user.deletion_requested_at
    return {
        "enabled": bool(enabled),
        "deletion_requested_at": requested.isoformat() if requested else None,
        "pending_deletion_at": pending.isoformat() if pending else None,
    }


@router.post("/logout")
async def portal_logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Clear the portal cookie and revoke the server-side session.

    Stamps ``user_profiles.tokens_invalidated_at`` so a leaked ``rq_token``
    cannot be replayed after the legitimate owner clicked "logout". The
    handler is intentionally tolerant: a missing or already-revoked
    cookie still returns 200 so the frontend logout flow stays
    idempotent.
    """
    response.delete_cookie(key=PORTAL_COOKIE_NAME, path="/")
    token = request.cookies.get(PORTAL_COOKIE_NAME)
    payload = decode_access_token(token) if token else None
    username = (payload or {}).get("sub")
    if username:
        try:
            user = (
                await db.execute(select(User).where(User.username == username))
            ).scalar_one_or_none()
            if user:
                await db.execute(
                    update(UserProfile)
                    .where(UserProfile.user_id == user.id)
                    .values(tokens_invalidated_at=datetime.now(timezone.utc))
                )
                await db.commit()
        except Exception as exc:
            logger.warning(
                "[PORTAL_LOGOUT] token revoke failed for user=%s: %s", username, exc,
            )
            await db.rollback()
    return {"ok": True}
