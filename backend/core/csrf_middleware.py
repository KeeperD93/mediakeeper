"""Global CSRF middleware for authenticated mutations.

Protects every POST/PUT/DELETE/PATCH request that carries either the backoffice
cookie (``mk_token``) or the Portal cookie (``rq_token``). The check is
skipped for safe methods, for the public ``/api/health`` endpoint, and for
requests without any authentication cookie (those will be rejected downstream
by the auth dependencies).

Login endpoints (``/api/auth/login``, ``/api/portal/auth/login``) bootstrap
the CSRF cookie themselves so the double-submit token cannot be checked on
the very first call — but Origin / Referer **is** still verified when
present, which is enough to block cross-site forced-login flows ("login
CSRF") without breaking legitimate clients that omit Origin (curl, mobile
SDKs).

The frontend reads ``mk_csrf`` and echoes it in the ``X-CSRF-Token`` header
via ``useApi.buildApiHeaders``.
"""
from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.auth._cookies import COOKIE_NAME, PORTAL_COOKIE_NAME
from api.auth._csrf import CSRF_COOKIE_NAME
from core.csrf_helpers import request_origin, same_origin

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Fully exempt from every CSRF check — public, no auth side-effect.
EXEMPT_PATHS = {
    "/api/health",
}

# Login bootstraps the CSRF cookie itself. The double-submit token check
# is skipped on these paths but the Origin / Referer guard still runs.
LOGIN_PATHS = {
    "/api/auth/login",
    "/api/portal/auth/login",
}


def _reject(detail: str) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": detail})


def _origin_matches(request) -> bool:
    """Run the Origin / Referer guard. Returns ``True`` when the request
    is same-origin or carries no origin claim at all (curl-like clients);
    returns ``False`` only when the header is present and points at a
    different origin."""
    expected_origin = request_origin(request)
    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")
    if origin and not same_origin(origin, expected_origin):
        return False
    if not origin and referer and not same_origin(referer, expected_origin):
        return False
    return True


class CsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        method = request.method.upper()
        if method in SAFE_METHODS:
            return await call_next(request)

        path = request.url.path
        if path in EXEMPT_PATHS:
            return await call_next(request)

        if path in LOGIN_PATHS:
            # Login forge protection: cross-origin POST is refused even
            # without an existing CSRF cookie. Missing Origin / Referer
            # falls through (legitimate non-browser clients).
            if not _origin_matches(request):
                return _reject("csrf_origin_mismatch")
            return await call_next(request)

        has_admin_cookie = bool(request.cookies.get(COOKIE_NAME))
        has_portal_cookie = bool(request.cookies.get(PORTAL_COOKIE_NAME))
        if not has_admin_cookie and not has_portal_cookie:
            return await call_next(request)

        if not _origin_matches(request):
            return _reject("csrf_origin_mismatch")

        cookie_token = (request.cookies.get(CSRF_COOKIE_NAME) or "").strip()
        header_token = (request.headers.get("x-csrf-token") or "").strip()
        if not cookie_token or not header_token:
            return _reject("csrf_token_invalid")
        if not secrets.compare_digest(cookie_token, header_token):
            return _reject("csrf_token_invalid")

        return await call_next(request)
