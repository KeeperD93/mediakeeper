"""Shared CSRF helpers for origin resolution.

Both the global CSRF middleware (``core.csrf_middleware``) and the
backoffice ``require_csrf`` dependency (``api.auth._csrf``) need to resolve
the canonical ``scheme://host`` of an incoming request — including when it
comes through a reverse proxy. Keeping a single implementation here
prevents the two copies from drifting apart.

Trust model: ``X-Forwarded-Host`` is honoured **only** when the request
comes from a proxy whitelisted in ``TRUSTED_PROXIES`` (decided by
``core.proxy.ProxyHeadersMiddleware``). The scheme is always read from
``request.url.scheme`` since the middleware rewrites it for trusted
proxies and leaves it untouched otherwise.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request

from core.proxy import trusted_forwarded_host


def request_origin(request: Request) -> str:
    """Return the canonical ``scheme://host`` of ``request``."""
    scheme = request.url.scheme
    host = trusted_forwarded_host(request) or request.headers.get("host") or request.url.netloc
    return f"{scheme}://{host}"


def same_origin(url: str, expected_origin: str) -> bool:
    """Return ``True`` if ``url`` shares the same ``scheme://host`` as
    ``expected_origin``.

    Empty or relative URLs are treated as same-origin: they make no
    cross-origin claim that the caller could verify.
    """
    if not url:
        return True
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return True
    return f"{parsed.scheme}://{parsed.netloc}" == expected_origin
