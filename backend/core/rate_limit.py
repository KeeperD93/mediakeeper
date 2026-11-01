"""Shared slowapi limiter and key helpers.

Lives outside ``main.py`` so route modules can decorate handlers with
``@limiter.limit(...)`` without an import cycle. ``main`` re-exports the
same instance to bind the middleware and exception handler.

storage=in-memory: acceptable for single-instance deployments (NAS).
Switch ``storage_uri`` to redis://... if MediaKeeper ever runs as
multi-replica; the per-IP buckets currently live in the worker
process only.
"""
from __future__ import annotations

import time
from math import ceil

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from constants.auth import COOKIE_NAME, PORTAL_COOKIE_NAME
from constants.security import LOGIN_RATE_LIMITED, UNKNOWN_CLIENT_IP
from core.proxy import get_client_ip
from core.security import decode_access_token


def ip_key(request: Request) -> str:
    """Slowapi default key — real client IP after proxy header rewrite, or one
    shared bucket when the request carries no usable IP."""
    return get_client_ip(request) or UNKNOWN_CLIENT_IP


def admin_user_or_ip_key(request: Request) -> str:
    """Key on the authenticated admin username when available, fall back
    to the client IP otherwise. Used by ``/api/auth/change-password`` so
    the quota tracks the account, not the network egress — a router NAT
    sharing one IP across the household must not throttle a legitimate
    user just because someone else hit ``/login`` recently.
    """
    token = request.cookies.get(COOKIE_NAME)
    if token:
        payload = decode_access_token(token)
        username = (payload or {}).get("sub")
        if username:
            return f"user:{username}"
    return f"ip:{ip_key(request)}"


def portal_user_or_ip_key(request: Request) -> str:
    """Same idea as ``admin_user_or_ip_key`` but on the Portal cookie.
    Used by hot endpoints (availability lookup, chat send) where a
    legitimate user must keep their own per-account budget intact even
    when sharing an IP with the rest of the household."""
    token = request.cookies.get(PORTAL_COOKIE_NAME)
    if token:
        payload = decode_access_token(token)
        username = (payload or {}).get("sub")
        if username:
            return f"user:{username}"
    return f"ip:{ip_key(request)}"


limiter = Limiter(key_func=ip_key, default_limits=["120/minute"])


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """The sign-in limit gives its code and its wait, for the sign-in page to show.
    Any other 429 keeps slowapi's body, which the shared toast speaks for."""
    if exc.detail != LOGIN_RATE_LIMITED:
        return _rate_limit_exceeded_handler(request, exc)
    item, keys = request.state.view_rate_limit
    reset_at = limiter.limiter.get_window_stats(item, *keys).reset_time
    return JSONResponse(
        {"detail": LOGIN_RATE_LIMITED},
        status_code=429,
        headers={"Retry-After": str(max(1, ceil(reset_at - time.time())))},
    )
