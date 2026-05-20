"""CSRF protection for cookie-authenticated backoffice endpoints."""
import secrets

from fastapi import HTTPException, Request, Response, status

from core.csrf_helpers import request_origin, same_origin
from core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_cookie_samesite,
    should_use_secure_cookies,
)

from ._cookies import COOKIE_NAME

CSRF_COOKIE_NAME = "mk_csrf"

# Mirror the JWT cookie lifetime so a valid session always has a matching
# CSRF cookie (otherwise the CSRF cookie expires first and every state-
# changing call returns 403 until the user refreshes).
_CSRF_COOKIE_MAX_AGE_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _set_csrf_cookie(response: Response, token: str, request: Request) -> None:
    secure_cookie = should_use_secure_cookies(request)
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        secure=secure_cookie,
        samesite=get_cookie_samesite(request),
        path="/",
        max_age=_CSRF_COOKIE_MAX_AGE_SECONDS,
    )


def ensure_csrf_cookie(response: Response, request: Request) -> str:
    token = (request.cookies.get(CSRF_COOKIE_NAME) or "").strip()
    if not token:
        token = secrets.token_urlsafe(32)
    _set_csrf_cookie(response, token, request)
    return token


def clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


async def require_csrf(request: Request) -> None:
    if not request.cookies.get(COOKIE_NAME):
        return

    expected_origin = request_origin(request)
    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")
    if origin and not same_origin(origin, expected_origin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf_origin_mismatch")
    if not origin and referer and not same_origin(referer, expected_origin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf_origin_mismatch")

    csrf_cookie = (request.cookies.get(CSRF_COOKIE_NAME) or "").strip()
    csrf_header = (request.headers.get("x-csrf-token") or "").strip()
    if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf_token_invalid")
