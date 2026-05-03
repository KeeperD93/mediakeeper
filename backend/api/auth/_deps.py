"""FastAPI dependency: resolve the current user via a JWT cookie/header."""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import (
    decode_access_token,
    is_backoffice_admin,
    is_token_valid_for_revocation_pivot,
)
from models.user import User

from ._cookies import COOKIE_NAME


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Verify the JWT cookie and return the current admin user.

    Cookies-only on purpose: the legacy ``Authorization: Bearer`` fallback
    was removed so a stolen JWT can no longer be replayed via header.
    """
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")

    payload = decode_access_token(token)
    if not payload or payload.get("scope") != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_invalid")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_invalid")

    result = await db.execute(select(User).where(User.username == username))
    user   = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
    if not is_token_valid_for_revocation_pivot(payload.get("iat"), user.tokens_invalidated_at):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session_revoked",
        )
    # Blocking of imported Emby/Jellyfin accounts is already done at login.
    # Here we avoid a bcrypt.checkpw on every protected request.
    if not is_backoffice_admin(user.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="backoffice_forbidden",
        )

    ALLOWED_PATHS = {"/api/auth/change-password", "/api/auth/me", "/api/auth/preferences", "/api/auth/refresh", "/api/auth/logout"}
    if user.must_change_password and request.url.path not in ALLOWED_PATHS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="must_change_password",
        )

    return user
