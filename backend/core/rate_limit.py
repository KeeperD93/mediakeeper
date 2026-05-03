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

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.proxy import get_client_ip
from core.security import decode_access_token


def ip_key(request: Request) -> str:
    """Slowapi default key — real client IP after proxy header rewrite."""
    return get_client_ip(request) or get_remote_address(request)


def admin_user_or_ip_key(request: Request) -> str:
    """Key on the authenticated admin username when available, fall back
    to the client IP otherwise. Used by ``/api/auth/change-password`` so
    the quota tracks the account, not the network egress — a router NAT
    sharing one IP across the household must not throttle a legitimate
    user just because someone else hit ``/login`` recently.
    """
    token = request.cookies.get("mk_token")
    if token:
        payload = decode_access_token(token)
        username = (payload or {}).get("sub")
        if username:
            return f"user:{username}"
    return f"ip:{ip_key(request)}"


limiter = Limiter(key_func=ip_key, default_limits=["120/minute"])
