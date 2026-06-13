"""Application-level DNS resolution cache.

When the admin opts into ``network.dns_cache_enabled``, we replace
``socket.getaddrinfo`` with a thin wrapper that memoises the answer
for a configurable TTL. Every outbound TCP connection from the
process (httpx, asyncpg, smtplib, …) inherits the cache automatically.

Why ship this for MediaKeeper:
- Bare-metal deployments without Docker often lack a system-level
  resolver cache, so each outbound call pays the DNS round trip.
- Even with ``systemd-resolved`` enabled, the in-process snapshot
  saves the IPC hop to the resolver daemon.

Why guard it behind a toggle:
- A stale cache entry survives a DNS change inside the TTL window;
  not great if you're rotating providers.
- The monkeypatch is process-global; users running specialised
  network stacks may prefer to disable it.

Stats expose the readout the admin panel needs (hits, misses, keys,
synthetic ``value_bytes`` for the table layout consistency).
"""
from __future__ import annotations

import logging
import socket
import sys
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.env_flags import env_int
from services.settings import get_setting

logger = logging.getLogger("mediakeeper.portal.dns_cache")

SETTING_KEY = "network.dns_cache_enabled"
TTL_SETTING_KEY = "network.dns_cache_ttl_seconds"

_DEFAULT_TTL = env_int("MK_DNS_CACHE_TTL_SECONDS", 300)

# In-memory cache. Each key maps to ``(records, expires_at, host)``
# — keeping the host alongside the records lets the readout name
# every entry without an extra reverse-lookup.
_cache: dict[tuple, tuple[list, float, str]] = {}
_stats: dict[str, int] = {"hits": 0, "misses": 0}
_ttl_seconds = _DEFAULT_TTL

_original_getaddrinfo: Any | None = None
_enabled = False


def _cached_getaddrinfo(host, port, *args, **kwargs):
    """Drop-in for ``socket.getaddrinfo`` that absorbs duplicate lookups."""
    # We key on the visible arguments — different ``family``/``type``/
    # ``proto`` combinations yield genuinely different answers, so we
    # honour them in the cache key.
    key = (host, port, args, tuple(sorted(kwargs.items())))
    now = time.time()
    cached = _cache.get(key)
    if cached is not None:
        records, expires, _name = cached
        if now < expires:
            _stats["hits"] += 1
            return records

    # Cache miss — defer to the real resolver. Always fall back to
    # the saved original so a partial monkeypatch can be undone.
    real = _original_getaddrinfo or socket.getaddrinfo
    records = real(host, port, *args, **kwargs)
    _cache[key] = (records, now + _ttl_seconds, str(host))
    _stats["misses"] += 1
    return records


def enable(ttl_seconds: int | None = None) -> None:
    """Install the monkeypatch + reset state.

    Idempotent: enabling twice is a no-op. ``ttl_seconds`` updates
    the in-memory TTL without flushing the existing entries — useful
    when the admin saves a new value mid-flight.
    """
    global _original_getaddrinfo, _enabled, _ttl_seconds
    if ttl_seconds is not None:
        _ttl_seconds = max(1, int(ttl_seconds))
    if _enabled:
        return
    _original_getaddrinfo = socket.getaddrinfo
    socket.getaddrinfo = _cached_getaddrinfo  # type: ignore[assignment]
    _enabled = True
    logger.info(f"dns_cache: enabled (TTL={_ttl_seconds}s)")


def disable() -> None:
    """Restore the stock resolver. Safe to call when already off."""
    global _enabled
    if not _enabled:
        return
    if _original_getaddrinfo is not None:
        socket.getaddrinfo = _original_getaddrinfo  # type: ignore[assignment]
    _enabled = False
    logger.info("dns_cache: disabled")


def is_enabled() -> bool:
    return _enabled


async def refresh_from_settings(db: AsyncSession) -> bool:
    """Re-read the toggle + TTL and align the runtime state.

    Returns the resolved enable state. Designed to be called at
    startup and whenever the admin saves the Network settings.
    """
    raw_enabled = await get_setting(db, SETTING_KEY)
    raw_ttl = await get_setting(db, TTL_SETTING_KEY)
    enabled_wanted = (raw_enabled or "").strip().lower() == "true"
    ttl_wanted = _DEFAULT_TTL
    if raw_ttl:
        try:
            ttl_wanted = max(1, int(raw_ttl))
        except (TypeError, ValueError):
            logger.warning(
                f"dns_cache: invalid TTL setting {raw_ttl!r}, keeping default"
            )
    if enabled_wanted:
        enable(ttl_seconds=ttl_wanted)
    else:
        disable()
    return enabled_wanted


def get_cache_stats() -> dict:
    """Snapshot for the admin readout — shape matches other caches."""
    # Drop entries whose TTL has elapsed so the ``keys`` number
    # matches what an upstream lookup would actually hit.
    now = time.time()
    expired = [k for k, (_r, exp, _n) in _cache.items() if exp < now]
    for k in expired:
        _cache.pop(k, None)
    # ``value_bytes`` is a rough estimate so the admin table can show
    # something comparable to the other caches — getaddrinfo records
    # are tuples of small primitives.
    value_bytes = sum(sys.getsizeof(v) for v in _cache.values())
    return {
        "name": "DNS cache",
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "keys": len(_cache),
        "max_keys": None,
        "ttl_seconds": _ttl_seconds,
        "value_bytes": value_bytes,
    }


def clear_cache() -> int:
    """Drop every entry + reset the counters. Returns the prior size."""
    n = len(_cache)
    _cache.clear()
    _stats["hits"] = 0
    _stats["misses"] = 0
    return n
