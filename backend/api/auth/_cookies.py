"""JWT cookie helpers for the admin backoffice and portal."""
from fastapi import Request, Response

from core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_cookie_samesite,
    should_use_secure_cookies,
)

# Admin JWT cookie name.
COOKIE_NAME = "mk_token"
# The portal uses a distinct cookie so an Emby-authenticated user can
# never reach the backoffice, even if rq_token leaks.
PORTAL_COOKIE_NAME = "rq_token"

# Keep the cookie alive exactly as long as the token it carries.
# If the operator raises JWT_EXPIRE_MINUTES, the cookie follows; without
# this, the cookie would silently expire before the token and force a
# reconnect even though the JWT is still valid.
_COOKIE_MAX_AGE_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _set_jwt_cookie(response: Response, token: str, request: Request):
    """Place the JWT in a secure httpOnly cookie."""
    secure_cookie = should_use_secure_cookies(request)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure_cookie,
        samesite=get_cookie_samesite(request),
        path="/",
        max_age=_COOKIE_MAX_AGE_SECONDS,
    )


def _clear_jwt_cookie(response: Response):
    """Clear the admin JWT cookie."""
    response.delete_cookie(key=COOKIE_NAME, path="/")


def _set_portal_jwt_cookie(response: Response, token: str, request: Request):
    """Place the portal JWT in a secure httpOnly cookie."""
    secure_cookie = should_use_secure_cookies(request)
    response.set_cookie(
        key=PORTAL_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure_cookie,
        samesite=get_cookie_samesite(request),
        path="/",
        max_age=_COOKIE_MAX_AGE_SECONDS,
    )
