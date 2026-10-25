"""Reverse-proxy trust + client IP helpers.

Strict whitelist driven by env ``TRUSTED_PROXIES`` (CSV of CIDR or IPs).
When the direct TCP client matches a trusted proxy, we honour the
``X-Forwarded-*`` chain to recover the real client info; otherwise we
ignore the headers entirely (failsafe for direct LAN exposure).

A custom middleware is used instead of ``uvicorn.middleware.proxy_headers``
(pinned to loopback in ``entrypoint.sh``) to validate each
``X-Forwarded-For`` hop it reads, to honour ``X-Forwarded-Host`` (uvicorn
does not rewrite the Host header) and to set an explicit
``request.state.from_trusted_proxy`` flag, read by the CSRF Origin check.
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
            net = ipaddress.ip_network(token, strict=False)
        except ValueError:
            logger.warning("Ignoring invalid TRUSTED_PROXIES entry: %r", token)
            continue
        networks.append(net)
        # A very broad CIDR makes every client look trusted, so X-Forwarded-*
        # (Origin / proto / client IP) would be honoured from anyone. Accept
        # it (the operator may know what they are doing) but warn loudly.
        if net.prefixlen == 0 or (net.version == 4 and net.prefixlen < 8):
            logger.warning(
                "TRUSTED_PROXIES entry %r is very broad (%s); restrict it to "
                "your reverse proxy's address.", token, net,
            )
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


def normalize_ip(raw: str | None) -> str | None:
    """Return ``raw`` as a canonical IP string, or ``None`` if it is not one.

    Accepts what proxies write in ``X-Forwarded-For``: a bare address,
    ``IPv4:port`` or ``[IPv6]:port``. The zone id is dropped and an
    IPv4-mapped address becomes IPv4, so one client always gets the same
    key and the result fits the 64-character IP columns.
    """
    value = (raw or "").strip()
    if value.startswith("["):
        value = value[1:].split("]", 1)[0]
    elif value.count(":") == 1:
        value = value.split(":", 1)[0]
    value = value.split("%", 1)[0]
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return str(ip)


def _forwarded_client(header_values: list[str], peer: str, networks: list[_Network]) -> str:
    """Return the rightmost ``X-Forwarded-For`` hop that is not a trusted proxy.

    Each proxy appends the address it received the request from, so only the
    hops added by trusted proxies are believed; anything further left was
    written by the client. A malformed hop ends the walk on the last good one,
    and when every hop is trusted the leftmost is kept.
    """
    client = peer
    hops = [hop for value in header_values for hop in value.split(",") if hop.strip()]
    for hop in reversed(hops):
        ip = normalize_ip(hop)
        if ip is None:
            break
        client = ip
        if not is_trusted_proxy_host(ip, networks):
            break
    return client


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """Honour ``X-Forwarded-*`` only when the direct TCP client is whitelisted.

    When the proxy is trusted:
      - ``request.client.host`` becomes the rightmost ``X-Forwarded-For`` IP
        that is not itself a trusted proxy (see ``_forwarded_client``).
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
            forwarded = request.headers.getlist("x-forwarded-for")
            if forwarded and client is not None:
                xff_ip = _forwarded_client(forwarded, client[0], self._networks)
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
    """Return the best-known client IP — already rewritten by middleware.

    Normalized here as well: uvicorn may have rewritten the client itself
    for a loopback peer, and callers store the value.
    """
    client = request.scope.get("client")
    if not client:
        return None
    return normalize_ip(client[0])


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
