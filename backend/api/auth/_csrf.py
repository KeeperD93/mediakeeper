"""CSRF protection for cookie-authenticated backoffice endpoints."""
import re
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

# Allowlist for an incoming CSRF cookie value. base64url charset matches
# what secrets.token_urlsafe produces; the 32-128 window covers today's
# 32-byte tokens (~43 chars) and leaves headroom for a future entropy
# bump without forcing a code change. Any value outside the window is
# treated as injected / tampered and replaced with a fresh token.
_CSRF_TOKEN_RE = re.compile(r"\A[A-Za-z0-9_-]{32,128}\Z")
_CSRF_TOKEN_BYTES = 32


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


def _is_valid_csrf_token(raw: str) -> bool:
    """Return True when ``raw`` matches the base64url charset and the
    32-128 length window expected of a server-issued CSRF token.

    Extracted so the validation has a single name in the codebase and a
    dedicated set of unit tests; ``ensure_csrf_cookie`` keeps a tampered
    or oversized incoming cookie value from reaching ``response.set_cookie``
    by replacing it with a fresh ``secrets.token_urlsafe`` when this guard
    returns False.
    """
    return _CSRF_TOKEN_RE.fullmatch(raw) is not None


def ensure_csrf_cookie(response: Response, request: Request) -> str:
    """Authenticated polls (``/me``, ``/refresh``) — reuse the existing
    cookie when it matches the allowlist, otherwise mint a fresh token.

    Preserves the double-submit token across concurrent SPA requests so a
    poll does not invalidate a header issued just before by another tab.
    Auth boundaries (login, change-password) must use
    :func:`rotate_csrf_cookie` instead.
    """
    raw = (request.cookies.get(CSRF_COOKIE_NAME) or "").strip()
    token = raw if _is_valid_csrf_token(raw) else secrets.token_urlsafe(_CSRF_TOKEN_BYTES)
    _set_csrf_cookie(response, token, request)
    return token


def rotate_csrf_cookie(response: Response, request: Request) -> str:
    """Auth boundaries (login, portal-login, change-password) — always
    generate a fresh token, ignoring any pre-existing cookie value.

    Closes the session-fixation window: a value pre-posed on the victim's
    browser before login (XSS subdomain, MITM HTTP, subdomain takeover)
    does not survive the auth boundary.
    """
    token = secrets.token_urlsafe(_CSRF_TOKEN_BYTES)
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
