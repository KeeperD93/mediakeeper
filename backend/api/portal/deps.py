"""Portal auth dependencies: profile loading and role checks."""
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_access_token, is_token_valid_for_revocation_pivot
from api.auth import PORTAL_COOKIE_NAME
from models.user import User
from models.portal.profile import UserProfile
from services.portal._display_name import parse_accept_language


async def get_request_lang(
    accept_language: str | None = Header(default=None, alias="accept-language"),
) -> str:
    """Resolve the viewer's display locale from the Accept-Language header.

    Returns ``"fr"`` or ``"en"`` — the only two locales the portal
    surfaces today. Drives the anonymous-pseudo alias localization.
    """
    return parse_accept_language(accept_language)


async def get_portal_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the current portal user.

    Reads the portal-specific ``rq_token`` cookie exclusively. This
    function deliberately does NOT accept the admin ``mk_token``
    cookie — the two auth surfaces are kept strictly separate so an
    admin browsing the MediaKeeper UI cannot inadvertently grant
    themselves portal permissions, and vice versa.

    The only exception is the token's ``scope`` claim, which must
    equal ``"portal"`` (set by ``authenticate_emby_user``). Tokens
    forged from the admin cookie would not carry this claim.
    """
    token = request.cookies.get(PORTAL_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")

    payload = decode_access_token(token)
    if not payload or payload.get("scope") != "portal":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_invalid")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_invalid")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
    return user


async def get_current_profile(
    request: Request,
    current_user: User = Depends(get_portal_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, UserProfile]:
    """Returns (User, UserProfile). Refuses if missing, disabled or revoked."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="profile_missing",
        )
    if not profile.account_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account_disabled",
        )
    # Force-logout: every JWT issued before ``tokens_invalidated_at`` is
    # rejected so the admin can kick a session in one click.
    if profile.tokens_invalidated_at:
        token = request.cookies.get(PORTAL_COOKIE_NAME)
        payload = decode_access_token(token) if token else None
        iat = (payload or {}).get("iat")
        if not is_token_valid_for_revocation_pivot(iat, profile.tokens_invalidated_at):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="session_revoked",
            )
    return current_user, profile


async def require_admin(
    user_profile: tuple[User, UserProfile] = Depends(get_current_profile),
) -> tuple[User, UserProfile]:
    """Requires admin role."""
    user, profile = user_profile
    if profile.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin_required",
        )
    return user, profile


# Granular permission keys mirrored on UserProfile (migration 035).
# Admins always pass — they would otherwise lose the ability to fix the
# very flag that locks them out.
_PERMISSION_COLUMNS = (
    "can_chat", "can_portal", "can_problems", "can_lists", "can_earn_xp_offline",
)


def require_permission(key: str):
    """FastAPI dependency factory for the granular permission flags
    introduced by the premium admin "Users" page (migration 035).

    Usage::

        @router.post("", dependencies=[Depends(require_permission("can_portal"))])

    Raises 403 with detail ``permission_denied:<key>`` when the flag is
    off. Admins always pass.
    """
    if key not in _PERMISSION_COLUMNS:
        raise ValueError(f"Unknown permission key: {key}")

    async def _check(
        user_profile: tuple[User, UserProfile] = Depends(get_current_profile),
    ) -> tuple[User, UserProfile]:
        user, profile = user_profile
        if profile.role == "admin":
            return user, profile
        if not bool(getattr(profile, key, False)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"permission_denied:{key}",
            )
        return user, profile

    return _check
