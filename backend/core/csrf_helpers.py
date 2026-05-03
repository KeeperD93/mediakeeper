"""Shared CSRF helpers for origin resolution.

Both the global CSRF middleware (``core.csrf_middleware``) and the
backoffice ``require_csrf`` dependency (``api.auth._csrf``) need to resolve
the canonical ``scheme://host`` of an incoming request — including when it
comes through a reverse proxy. Keeping a single implementation here
prevents the two copies from drifting apart.

The chat WebSocket handshake reuses the same logic via
``websocket_canonical_origin`` so the auto-derive Origin guard is
symmetric across HTTP and WS in both deployment modes:

* Mode A — direct LAN exposure (``TRUSTED_PROXIES`` empty). The
  canonical origin is built from the request scheme + the ``Host``
  header.
* Mode B — behind a trusted reverse proxy (Caddy, Synology DSM,
  nginx-proxy-manager…). ``X-Forwarded-Host`` and ``X-Forwarded-Proto``
  are honoured only when the direct TCP client matches a network in
  ``TRUSTED_PROXIES``.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request
from starlette.websockets import WebSocket

from core.proxy import (
    TRUSTED_PROXIES,
    is_trusted_proxy_host,
    trusted_forwarded_host,
)

# Map ASGI WebSocket schemes to their HTTP equivalent so the
# canonical-origin comparison stays uniform: a browser opens a WS
# handshake from an ``https://`` page even though the URL becomes
# ``wss://`` once the upgrade succeeds.
_WS_TO_HTTP_SCHEME = {"ws": "http", "wss": "https"}


def request_origin(request: Request) -> str:
    """Return the canonical ``scheme://host`` of ``request``."""
    scheme = request.url.scheme
    host = trusted_forwarded_host(request) or request.headers.get("host") or request.url.netloc
    return f"{scheme}://{host}"


def websocket_canonical_origin(websocket: WebSocket) -> str:
    """Return the HTTP-style canonical origin for a WebSocket handshake.

    The flag set by ``ProxyHeadersMiddleware`` does not exist on the WS
    path (Starlette runs ``BaseHTTPMiddleware`` on HTTP only), so we
    re-derive the trust signal from the direct TCP client and apply the
    same precedence: trusted proxy → ``X-Forwarded-Host`` /
    ``X-Forwarded-Proto`` ; otherwise the local ``Host`` and the
    raw ASGI scheme.
    """
    scope = websocket.scope
    raw_scheme = scope.get("scheme") or "ws"
    scheme = _WS_TO_HTTP_SCHEME.get(raw_scheme, raw_scheme)

    client = scope.get("client") or (None, None)
    client_host = client[0] if client else None
    direct_from_proxy = bool(TRUSTED_PROXIES) and is_trusted_proxy_host(client_host)

    host: str | None = None
    if direct_from_proxy:
        forwarded = websocket.headers.get("x-forwarded-host", "")
        if forwarded:
            host = forwarded.split(",", 1)[0].strip() or None
        forwarded_proto = websocket.headers.get("x-forwarded-proto", "")
        if forwarded_proto:
            scheme = forwarded_proto.split(",", 1)[0].strip().lower() or scheme
    if not host:
        host = websocket.headers.get("host") or scope.get("server", ("",))[0]
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
