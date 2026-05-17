"""``/api/settings/network`` GET / PUT contract + cache propagation.

Pins:
- GET returns the three values with safe defaults when nothing is
  persisted yet.
- PUT honours ``model_fields_set`` — only the keys present in the
  payload are written.
- Toggling a cache via the endpoint triggers the live refresh on
  the matching service (``image_cache.refresh_enabled_flag`` or
  ``dns_cache.refresh_from_settings``).
"""
from __future__ import annotations

import pytest


async def _login_admin(client, monkeypatch) -> None:
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "TestPassword123!"},
    )
    assert resp.status_code == 200, resp.text


@pytest.fixture(autouse=True)
def _reset_dns_cache_state():
    """Make sure the monkeypatch isn't lingering from another test."""
    from services.portal import dns_cache
    dns_cache.disable()
    dns_cache._cache.clear()
    dns_cache._stats["hits"] = 0
    dns_cache._stats["misses"] = 0
    yield
    dns_cache.disable()


@pytest.mark.asyncio
async def test_get_returns_defaults_when_unset(client, admin_user, monkeypatch):
    """Fresh install → both caches OFF, TTL = 300."""
    await _login_admin(client, monkeypatch)

    resp = await client.get("/api/settings/network")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "image_cache_enabled": False,
        "dns_cache_enabled": False,
        "dns_cache_ttl_seconds": 300,
    }


@pytest.mark.asyncio
async def test_put_persists_partial_payload(client, admin_user, monkeypatch):
    """``model_fields_set`` keeps untouched values alone."""
    await _login_admin(client, monkeypatch)

    # Flip only the image cache toggle.
    resp = await client.put(
        "/api/settings/network", json={"image_cache_enabled": True}
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    body = (await client.get("/api/settings/network")).json()
    assert body["image_cache_enabled"] is True
    assert body["dns_cache_enabled"] is False  # untouched
    assert body["dns_cache_ttl_seconds"] == 300  # untouched


@pytest.mark.asyncio
async def test_put_propagates_image_cache_to_runtime(
    client, admin_user, monkeypatch,
):
    """Enabling the image cache flips the in-memory snapshot."""
    from services.portal import image_cache
    image_cache._enabled = False  # force a known starting state
    await _login_admin(client, monkeypatch)

    resp = await client.put(
        "/api/settings/network", json={"image_cache_enabled": True}
    )
    assert resp.status_code == 200
    assert image_cache.is_enabled() is True


@pytest.mark.asyncio
async def test_put_propagates_dns_cache_to_runtime(
    client, admin_user, monkeypatch,
):
    """Enabling the DNS cache installs the monkeypatch immediately."""
    from services.portal import dns_cache
    assert not dns_cache.is_enabled()
    await _login_admin(client, monkeypatch)

    resp = await client.put(
        "/api/settings/network",
        json={"dns_cache_enabled": True, "dns_cache_ttl_seconds": 60},
    )
    assert resp.status_code == 200
    assert dns_cache.is_enabled() is True
    assert dns_cache._ttl_seconds == 60

    # Toggling off restores the stock resolver.
    resp = await client.put(
        "/api/settings/network", json={"dns_cache_enabled": False}
    )
    assert resp.status_code == 200
    assert not dns_cache.is_enabled()


@pytest.mark.asyncio
async def test_put_clamps_ttl_to_minimum(client, admin_user, monkeypatch):
    """Negative / zero TTL is bumped to 1 instead of silently saved."""
    await _login_admin(client, monkeypatch)

    resp = await client.put(
        "/api/settings/network", json={"dns_cache_ttl_seconds": 0}
    )
    assert resp.status_code == 200

    body = (await client.get("/api/settings/network")).json()
    assert body["dns_cache_ttl_seconds"] == 1
