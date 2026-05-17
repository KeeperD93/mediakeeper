"""DNS resolver cache: monkeypatch behaviour + stats.

Pins:
- ``enable``/``disable`` swap ``socket.getaddrinfo`` in/out and are
  idempotent.
- Cache hits don't call the underlying resolver.
- Expired entries are purged on the next stats read.
- ``refresh_from_settings`` honours both ``network.dns_cache_enabled``
  and ``network.dns_cache_ttl_seconds``.
"""
from __future__ import annotations

import socket
import time

import pytest

from services.portal import dns_cache
from services.settings import set_setting


@pytest.fixture(autouse=True)
def _isolated_state(monkeypatch):
    """Each test starts with the patch removed + empty stats."""
    dns_cache.disable()
    dns_cache._cache.clear()
    dns_cache._stats["hits"] = 0
    dns_cache._stats["misses"] = 0
    yield
    dns_cache.disable()


def test_enable_swaps_getaddrinfo_and_disable_restores():
    original = socket.getaddrinfo
    dns_cache.enable(ttl_seconds=10)
    assert socket.getaddrinfo is dns_cache._cached_getaddrinfo
    dns_cache.disable()
    assert socket.getaddrinfo is original


def test_enable_is_idempotent():
    dns_cache.enable(ttl_seconds=10)
    patched_once = socket.getaddrinfo
    dns_cache.enable(ttl_seconds=10)
    assert socket.getaddrinfo is patched_once


def test_cache_hit_skips_underlying_resolver(monkeypatch):
    """Second lookup for the same host doesn't call the real resolver."""
    call_count = {"n": 0}

    def fake_resolver(host, port, *args, **kwargs):
        call_count["n"] += 1
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.2.3.4", port))]

    dns_cache._original_getaddrinfo = fake_resolver
    monkeypatch.setattr(socket, "getaddrinfo", dns_cache._cached_getaddrinfo)
    dns_cache._enabled = True

    dns_cache._cached_getaddrinfo("example.com", 443)
    dns_cache._cached_getaddrinfo("example.com", 443)
    dns_cache._cached_getaddrinfo("example.com", 443)

    assert call_count["n"] == 1
    assert dns_cache._stats["hits"] == 2
    assert dns_cache._stats["misses"] == 1


def test_expired_entries_are_dropped_on_stats_read():
    dns_cache._cache[("stale", 80, (), ())] = (
        [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("9.9.9.9", 80))],
        time.time() - 1,  # already expired
        "stale",
    )
    dns_cache._cache[("fresh", 80, (), ())] = (
        [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80))],
        time.time() + 60,
        "fresh",
    )
    stats = dns_cache.get_cache_stats()
    assert stats["keys"] == 1  # stale dropped


def test_clear_resets_state(monkeypatch):
    dns_cache._cache[("x", 80, (), ())] = (
        [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 80))],
        time.time() + 60,
        "x",
    )
    dns_cache._stats["hits"] = 5
    dns_cache._stats["misses"] = 3

    removed = dns_cache.clear_cache()
    assert removed == 1
    assert dns_cache._stats["hits"] == 0
    assert dns_cache._stats["misses"] == 0
    assert not dns_cache._cache


def test_stats_payload_shape():
    stats = dns_cache.get_cache_stats()
    for k in ("name", "hits", "misses", "keys", "max_keys", "ttl_seconds", "value_bytes"):
        assert k in stats
    assert stats["max_keys"] is None
    assert stats["ttl_seconds"] >= 1


@pytest.mark.asyncio
async def test_refresh_from_settings_enables_on_truthy_value(db_session):
    """Setting flips ON → resolver is replaced + TTL applied."""
    await set_setting(db_session, dns_cache.SETTING_KEY, "true")
    await set_setting(db_session, dns_cache.TTL_SETTING_KEY, "42")

    enabled = await dns_cache.refresh_from_settings(db_session)
    assert enabled is True
    assert dns_cache.is_enabled()
    assert dns_cache._ttl_seconds == 42


@pytest.mark.asyncio
async def test_refresh_from_settings_disables_when_off(db_session):
    """Setting flips OFF → resolver restored."""
    await set_setting(db_session, dns_cache.SETTING_KEY, "true")
    await dns_cache.refresh_from_settings(db_session)
    assert dns_cache.is_enabled()

    await set_setting(db_session, dns_cache.SETTING_KEY, "false")
    enabled = await dns_cache.refresh_from_settings(db_session)
    assert enabled is False
    assert not dns_cache.is_enabled()


@pytest.mark.asyncio
async def test_refresh_handles_invalid_ttl_gracefully(db_session):
    """Garbage in the TTL setting falls back to the default."""
    await set_setting(db_session, dns_cache.SETTING_KEY, "true")
    await set_setting(db_session, dns_cache.TTL_SETTING_KEY, "not-a-number")

    await dns_cache.refresh_from_settings(db_session)
    assert dns_cache._ttl_seconds == dns_cache._DEFAULT_TTL
