"""Reverse-proxy trust + client IP helpers.

Strict whitelist driven by env ``TRUSTED_PROXIES`` (CSV of CIDR or IPs).
When the direct TCP client matches a trusted proxy, we honour the
``X-Forwarded-*`` chain to recover the real client info; otherwise we
ignore the headers entirely (failsafe for direct LAN exposure).

A custom middleware is used instead of ``uvicorn.middleware.proxy_headers``
to gain three properties: explicit CIDR support, validation of
``X-Forwarded-Host`` (uvicorn does not rewrite the Host header), and an
explicit ``request.state.from_trusted_proxy`` flag consulted by
downstream helpers (cookie Secure check, CSRF Origin check).
"""
from __future__ import annotations

import ipaddress
import logging
import os
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

logger = logging.getLogger("mediakeeper")

_Network = ipaddress.IPv4Network | ipaddress.IPv6Network


def parse_trusted_proxies(raw: str | None) -> list[_Network]:
    """Parse ``TRUSTED_PROXIES`` (CSV of IPs or CIDRs).

    Empty entries and parse failures are dropped — the latter are
    logged once at startup so a typo does not silently neutralise the
    proxy whitelist.
    """
    networks: list[_Network] = []
    for token in (raw or "").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            networks.append(ipaddress.ip_network(token, strict=False))
        except ValueError:
            logger.warning("Ignoring invalid TRUSTED_PROXIES entry: %r", token)
    return networks


TRUSTED_PROXIES: list[_Network] = parse_trusted_proxies(os.getenv("TRUSTED_PROXIES"))


def is_trusted_proxy_host(
    host: str | None,
    networks: Iterable[_Network] | None = None,
) -> bool:
    """Return True if ``host`` (an IP literal) is in the trusted set."""
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    pool = networks if networks is not None else TRUSTED_PROXIES
    return any(ip in net for net in pool)


def _first_xff(value: str | None) -> str | None:
    if not value:
        return None
    first = value.split(",", 1)[0].strip()
    return first or None


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """Honour ``X-Forwarded-*`` only when the direct TCP client is whitelisted.

    When the proxy is trusted:
      - ``request.client.host`` becomes the leftmost ``X-Forwarded-For`` IP.
      - ``request.url.scheme`` becomes the ``X-Forwarded-Proto`` value.
      - ``request.state.from_trusted_proxy`` is set to ``True``.

    When the proxy is not trusted (default — ``TRUSTED_PROXIES`` empty):
      - Forwarded headers are ignored entirely.
      - ``request.state.from_trusted_proxy`` is set to ``False``.
    """

    def __init__(self, app: ASGIApp, networks: Iterable[_Network] | None = None):
        super().__init__(app)
        self._networks: list[_Network] = (
            list(networks) if networks is not None else TRUSTED_PROXIES
        )

    async def dispatch(self, request: Request, call_next):
        scope = request.scope
        client = scope.get("client")
        client_host = client[0] if client else None

        if self._networks and is_trusted_proxy_host(client_host, self._networks):
            xff_ip = _first_xff(request.headers.get("x-forwarded-for"))
            if xff_ip and client is not None:
                scope["client"] = (xff_ip, client[1])

            xfp = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
            if xfp in {"http", "https"}:
                scope["scheme"] = xfp

            request.state.from_trusted_proxy = True
        else:
            request.state.from_trusted_proxy = False

        return await call_next(request)


def is_request_from_trusted_proxy(request: Request) -> bool:
    return bool(getattr(request.state, "from_trusted_proxy", False))


def get_client_ip(request: Request) -> str | None:
    """Return the best-known client IP — already rewritten by middleware."""
    client = request.scope.get("client")
    if not client:
        return None
    return client[0] or None


def is_request_secure(request: Request) -> bool:
    """True iff the request scheme is HTTPS (already rewritten by middleware)."""
    return request.url.scheme == "https"


def trusted_forwarded_host(request: Request) -> str | None:
    """Return ``X-Forwarded-Host`` iff the request comes from a trusted proxy."""
    if not is_request_from_trusted_proxy(request):
        return None
    raw = request.headers.get("x-forwarded-host")
    if not raw:
        return None
    return raw.split(",", 1)[0].strip() or None
