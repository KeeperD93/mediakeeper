"""URL safety helpers covering two distinct concerns.

1. Persistence-edge sanitisation (:func:`safe_url`).
   User-supplied URL fields (``user_list_items.poster_url`` today,
   more later) are filtered against an HTTPS-only / host-whitelist
   policy before they hit the database. Mirrors
   ``frontend/src/utils/safeUrl.js`` so server and client agree on
   what counts as a safe inline image URL.

2. Outbound-HTTP guards (:func:`is_allowed_image_url`,
   :func:`is_discord_webhook_url`, :func:`validate_outbound_url`).
   Server-side notifiers and the image proxy must never be coerced
   into hitting internal services (SSRF). The legacy prefix checks
   (``url.startswith("https://image.tmdb.org/")``) were bypassable
   with userinfo segments (``https://image.tmdb.org@evil.com/x``)
   and trailing-dot subdomain tricks. The helpers below extract the
   hostname through :func:`urllib.parse.urlparse` and compare it
   strictly, then — for outbound webhooks — resolve DNS and reject
   any name pointing at a private/loopback/link-local address.

DNS rebinding between :func:`validate_outbound_url` and the actual
httpx connect (TOCTOU) is mitigated by :mod:`core.safe_http`, which
pins the connect to a validated IP and preserves the original
hostname for SNI/cert verification.
"""
from __future__ import annotations

import asyncio
import ipaddress
import re
from typing import Iterable, Optional
from urllib.parse import urlparse

_BLOCKED_SCHEMES = frozenset({"javascript", "data", "vbscript", "file", "about"})
_DEFAULT_SCHEMES = frozenset({"https"})

#: TMDB CDN host — the only allowed upstream for the image proxy.
ALLOWED_IMAGE_HOST = "image.tmdb.org"

#: Hosts accepted for Discord webhooks. Both the modern domain and
#: the legacy alias Discord still honours.
ALLOWED_DISCORD_HOSTS = frozenset({"discord.com", "discordapp.com"})

#: Path prefix every Discord webhook URL must share. Matched after
#: the hostname check, never on the raw URL string.
_DISCORD_WEBHOOK_PATH_PREFIX = "/api/webhooks/"

#: Schemes accepted for any outbound HTTP. ``https`` only — no
#: ``http``, ``file``, ``gopher``, ``ftp``.
_ALLOWED_OUTBOUND_SCHEMES = frozenset({"https"})

# Tabs and newlines hidden inside a URL would let ``\tjavascript:`` slip
# past a naive ``startswith("http")`` check. ``urlparse`` itself ignores
# whitespace, but we strip first so we can also reject bare control
# characters defensively.
_WHITESPACE_RE = re.compile(r"\s+")


class UnsafeOutboundURL(ValueError):
    """Raised when an outbound URL fails safety validation.

    ``reason`` is a short slug suitable for log lines. Never surface
    the slug to end-users — it is meant for operator triage.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def safe_url(
    raw: Optional[str],
    *,
    schemes: Iterable[str] = _DEFAULT_SCHEMES,
    allowed_hosts: Optional[Iterable[str]] = None,
) -> Optional[str]:
    """Return ``raw`` when it parses as a safe URL, else ``None``.

    - ``schemes``: lowercase scheme names accepted (default: ``https``).
    - ``allowed_hosts``: when provided, the URL host (lowercased, no
      port) must match exactly one of these. ``None`` disables the
      host check.
    - ``javascript:``, ``data:``, ``vbscript:``, ``file:``, ``about:``
      are always rejected, even when included in ``schemes``.
    - Empty / non-string / whitespace-only inputs return ``None``.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        return None

    cleaned = _WHITESPACE_RE.sub("", raw).strip()
    if not cleaned:
        return None

    try:
        parsed = urlparse(cleaned)
    except ValueError:
        return None

    scheme = (parsed.scheme or "").lower()
    if not scheme:
        return None
    if scheme in _BLOCKED_SCHEMES:
        return None

    accepted = {s.lower() for s in schemes}
    if scheme not in accepted:
        return None

    host = (parsed.hostname or "").lower()
    if not host:
        return None

    if allowed_hosts is not None:
        whitelist = {h.lower() for h in allowed_hosts}
        if host not in whitelist:
            return None

    return cleaned


def _normalize_host(host: str | None) -> str:
    """Lowercase + strip trailing dot so subdomain tricks fail closed."""
    if not host:
        return ""
    return host.lower().rstrip(".")


def is_allowed_image_url(url: str) -> bool:
    """Return ``True`` iff ``url`` is a valid TMDB CDN image URL.

    Strict hostname equality against :data:`ALLOWED_IMAGE_HOST`, not a
    prefix or substring check. Rejects userinfo bypasses
    (``https://image.tmdb.org@evil.com/x``) and trailing-dot subdomain
    attacks (``https://image.tmdb.org.evil.com/x``).
    """
    if not isinstance(url, str) or not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in _ALLOWED_OUTBOUND_SCHEMES:
        return False
    return _normalize_host(parsed.hostname) == ALLOWED_IMAGE_HOST


def is_discord_webhook_url(url: str) -> bool:
    """Return ``True`` iff ``url`` is a syntactically valid Discord webhook.

    Strict hostname equality against :data:`ALLOWED_DISCORD_HOSTS` plus
    a path-prefix check on the parsed path (not the raw URL string —
    that catches ``https://discord.com@evil.com/api/webhooks/...``).
    """
    if not isinstance(url, str) or not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in _ALLOWED_OUTBOUND_SCHEMES:
        return False
    if _normalize_host(parsed.hostname) not in ALLOWED_DISCORD_HOSTS:
        return False
    return parsed.path.startswith(_DISCORD_WEBHOOK_PATH_PREFIX)


def is_private_address(host: str) -> bool:
    """Return ``True`` if ``host`` is an IP literal in a non-public range.

    Covers IPv4/IPv6 private, loopback, link-local, reserved, multicast
    and unspecified blocks. The IPv4-mapped-IPv6 form
    (``::ffff:192.168.x.x``) is unwrapped before the check so an
    attacker cannot bypass the IPv4 rule by encoding the same address
    in IPv6.

    Bracketed IPv6 literals (``[::1]``) are accepted: the brackets
    are stripped before parsing so the helper is safe to call with
    either form. ``ipaddress.ip_address`` itself rejects the bracketed
    spelling, which would otherwise produce a false-negative.
    """
    if host and host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


async def resolve_host(host: str) -> list[str]:
    """Resolve ``host`` to its IP literals via the running event loop.

    Returns the de-duplicated list of resolved addresses. An empty
    list signals resolution failure — callers treat that as unsafe.
    """
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, None)
    except OSError:
        return []
    seen: list[str] = []
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip = sockaddr[0]
        if ip and ip not in seen:
            seen.append(ip)
    return seen


async def validate_outbound_url(url: str) -> list[str]:
    """Validate ``url`` for outbound HTTP and return the safe IP list.

    Raises :class:`UnsafeOutboundURL` (with a short slug reason) when
    any check fails. The returned list of IP literals lets callers
    pin the connect through :mod:`core.safe_http` so DNS rebinding
    between this validation and the connect cannot redirect httpx to
    a private address.
    """
    if not isinstance(url, str) or not url:
        raise UnsafeOutboundURL("empty_url")
    try:
        parsed = urlparse(url)
    except ValueError as e:
        raise UnsafeOutboundURL("parse_failed") from e
    if parsed.scheme not in _ALLOWED_OUTBOUND_SCHEMES:
        raise UnsafeOutboundURL("scheme_not_allowed")
    host = _normalize_host(parsed.hostname)
    if not host:
        raise UnsafeOutboundURL("missing_host")
    if is_private_address(host):
        raise UnsafeOutboundURL("private_ip_literal")
    addrs = await resolve_host(host)
    if not addrs:
        raise UnsafeOutboundURL("dns_resolution_failed")
    for addr in addrs:
        if is_private_address(addr):
            raise UnsafeOutboundURL("dns_resolves_private")
    return addrs
