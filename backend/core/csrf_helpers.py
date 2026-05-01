"""Shared CSRF helpers for origin resolution.

Both the global CSRF middleware (``core.csrf_middleware``) and the
backoffice ``require_csrf`` dependency (``api.auth._csrf``) need to resolve
the canonical ``scheme://host`` of an incoming request — including when it
comes through a reverse proxy that injects ``X-Forwarded-Proto`` /
``X-Forwarded-Host``. Keeping a single implementation here prevents the two
copies from drifting apart.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request


def request_origin(request: Request) -> str:
    """Return the canonical ``scheme://host`` of ``request``.

    Honours ``X-Forwarded-Proto`` and ``X-Forwarded-Host`` when set by a
    reverse proxy; otherwise falls back to the request URL's own scheme
    and host.
    """
    headers = request.headers
    proto = headers.get("x-forwarded-proto")
    if proto:
        scheme = proto.split(",", 1)[0].strip()
    else:
        scheme = request.url.scheme

    host = headers.get("x-forwarded-host") or headers.get("host") or request.url.netloc
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
