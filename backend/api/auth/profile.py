"""Endpoints profil current : /me, /change-password, /refresh, /logout, /preferences."""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.proxy import get_client_ip
from core.rate_limit import admin_user_or_ip_key, limiter
from core.security import create_access_token, hash_password, verify_password
from models.user import User
from services.security import ensure_not_blocked, record_attempt, record_failure

from ._cookies import PORTAL_COOKIE_NAME, _clear_jwt_cookie, _set_jwt_cookie
from ._csrf import clear_csrf_cookie, ensure_csrf_cookie, require_csrf, rotate_csrf_cookie
from ._deps import get_current_user
from ._schemas import ChangePasswordRequest, LocaleRequest, PreferencesRequest

logger = logging.getLogger("mediakeeper.api.auth")
router = APIRouter()

# Scope name surfaced in the security dashboard alongside ``admin`` /
# ``portal``. Kept distinct so a series of failed change-password attempts
# does not auto-block the legitimate login flow on the same identity.
PASSWORD_CHANGE_SCOPE = "admin_password"  # noqa: S105 -- scope identifier, not a credential value


@router.get("/me")
async def get_me(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_csrf_cookie(response, request)
    # Surface the linked portal avatar (when present) so the admin
    # topbar can render the same MkAvatar shown on /portal/users.
    # ``UserProfile`` is 1:1 with ``User`` via user_id; the lookup
    # returns ``None`` for admins who never visited the portal side.
    from models.portal.profile import UserProfile
    avatar_row = (await db.execute(
        select(UserProfile.avatar_url).where(UserProfile.user_id == current_user.id)
    )).first()
    return {
        "username":             current_user.username,
        "must_change_password": current_user.must_change_password,
        "avatar_url":           avatar_row[0] if avatar_row else None,
    }


@router.post("/change-password")
@limiter.limit("5/minute", key_func=admin_user_or_ip_key)
async def change_password(
    req:          ChangePasswordRequest,
    request:      Request,
    response:     Response,
    csrf_protected: None = Depends(require_csrf),
    current_user: User = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    client_ip = get_client_ip(request) or "unknown"
    user_agent = request.headers.get("user-agent")
    await ensure_not_blocked(db, client_ip, current_user.username, PASSWORD_CHANGE_SCOPE)

    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="password_mismatch")

    if not verify_password(req.current_password, current_user.hashed_password):
        await record_failure(
            db, client_ip, current_user.username, PASSWORD_CHANGE_SCOPE, user_agent,
        )
        raise HTTPException(status_code=400, detail="current_password_invalid")

    if req.current_password == req.new_password:
        raise HTTPException(status_code=400, detail="new_password_must_differ")

    result = await db.execute(select(User).where(User.username == current_user.username))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")

    user.hashed_password      = hash_password(req.new_password)
    user.must_change_password = False
    # Stamp the revocation pivot before issuing the new token so every JWT
    # already minted for this account on other devices is rejected on the
    # next request, while the new token (iat == now) stays valid. The
    # pivot is floored to whole seconds because JWT ``iat`` is encoded
    # with second resolution.
    user.tokens_invalidated_at = datetime.now(timezone.utc).replace(microsecond=0)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await record_attempt(
        db, client_ip, user.username, PASSWORD_CHANGE_SCOPE, success=True, user_agent=user_agent,
    )
    new_token = create_access_token({"sub": user.username, "scope": "admin"})
    _set_jwt_cookie(response, new_token, request)
    rotate_csrf_cookie(response, request)
    logger.info(f"[PASSWORD] Password changed for user={user.username}")
    return {"success": True}


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    csrf_protected: None = Depends(require_csrf),
    current_user: User = Depends(get_current_user),
):
    """Renew le cookie JWT."""
    new_token = create_access_token({"sub": current_user.username, "scope": "admin"})
    _set_jwt_cookie(response, new_token, request)
    ensure_csrf_cookie(response, request)
    return {"success": True}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    csrf_protected: None = Depends(require_csrf),
):
    """Delete the admin JWT cookie AND any Requests session.

    Not clearing ``rq_token`` here would leave an admin who logs out
    of MediaKeeper still connected to the Requests area in the same
    browser — a possible bypass of the intended separation.
    """
    _clear_jwt_cookie(response)
    response.delete_cookie(key=PORTAL_COOKIE_NAME, path="/")
    clear_csrf_cookie(response)
    return {"success": True}


@router.get("/preferences")
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.settings import get_user_preferences
    row = await get_user_preferences(db, current_user.id)
    if not row or not row.preferences:
        return {"theme": "dark", "sidebar_collapsed": False}
    try:
        return json.loads(row.preferences)
    except Exception:
        return {"theme": "dark", "sidebar_collapsed": False}


@router.post("/preferences")
async def save_preferences(
    req: PreferencesRequest,
    csrf_protected: None = Depends(require_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.settings import upsert_user_preferences
    await upsert_user_preferences(db, current_user.id, preferences=json.dumps(req.model_dump()))
    return {"success": True}


@router.post("/locale")
async def save_locale(
    req: LocaleRequest,
    csrf_protected: None = Depends(require_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist just the locale field, merging with existing preferences."""
    from services.settings import get_user_preferences, upsert_user_preferences
    row = await get_user_preferences(db, current_user.id)
    current = {}
    if row and row.preferences:
        try:
            current = json.loads(row.preferences)
        except Exception:
            current = {}
    current["locale"] = req.locale
    await upsert_user_preferences(db, current_user.id, preferences=json.dumps(current))
    return {"success": True}
