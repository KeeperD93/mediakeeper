"""JWT cookie helpers for the admin backoffice and portal."""
from fastapi import Request, Response

from core.security import get_cookie_samesite, should_use_secure_cookies

# Admin JWT cookie name.
COOKIE_NAME = "mk_token"
# The portal uses a distinct cookie so an Emby-authenticated user can
# never reach the backoffice, even if rq_token leaks.
PORTAL_COOKIE_NAME = "rq_token"


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
        max_age=3600,
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
        max_age=3600,
    )
