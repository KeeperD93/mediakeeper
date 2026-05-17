"""Admin cache stats + clear endpoints.

The Seerr-style cache panel in Settings → Scheduler reads from
``GET /api/scheduler/caches`` and clears via
``POST /api/scheduler/caches/<id>/clear``. These tests pin the
shape of the readout and that ``clear`` resets both the entries
and the counters.
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


@pytest.mark.asyncio
async def test_list_caches_returns_tmdb_entry(client, admin_user, monkeypatch):
    await _login_admin(client, monkeypatch)

    resp = await client.get("/api/scheduler/caches")
    assert resp.status_code == 200
    payload = resp.json()
    assert "items" in payload
    ids = [c["id"] for c in payload["items"]]
    assert "tmdb" in ids

    tmdb = next(c for c in payload["items"] if c["id"] == "tmdb")
    # Required keys for the admin readout
    for k in ("name", "hits", "misses", "keys", "max_keys", "ttl_seconds", "value_bytes"):
        assert k in tmdb, f"missing key {k!r} in TMDB cache entry"
    assert tmdb["name"] == "The Movie Database API"
    assert tmdb["ttl_seconds"] == 300


@pytest.mark.asyncio
async def test_clear_cache_resets_counters(client, admin_user, monkeypatch):
    """After clear, hits/misses/keys are all zero."""
    from services.portal import tmdb_search

    await _login_admin(client, monkeypatch)

    # Force at least one miss + one hit so the counters move.
    from unittest.mock import AsyncMock, patch
    with patch(
        "services.portal.tmdb_search.search_tmdb_multi",
        new=AsyncMock(return_value=[]),
    ):
        await tmdb_search.search_with_cache(client_db := None or _none_db(), "warm")  # type: ignore[arg-type]

    # Pre-condition: counters are non-zero (the miss above bumped misses).
    stats_before = tmdb_search.get_cache_stats()
    assert stats_before["misses"] >= 1

    resp = await client.post("/api/scheduler/caches/tmdb/clear")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # ``cleared`` reflects the number of entries dropped.
    assert body["cleared"] >= 0

    stats_after = tmdb_search.get_cache_stats()
    assert stats_after["hits"] == 0
    assert stats_after["misses"] == 0
    assert stats_after["keys"] == 0


def _none_db():
    """The mocked ``search_tmdb_multi`` ignores its ``db`` argument,
    so passing ``None`` is enough to drive a no-result cache miss."""
    return None


@pytest.mark.asyncio
async def test_clear_cache_unknown_id_returns_404(client, admin_user, monkeypatch):
    await _login_admin(client, monkeypatch)
    resp = await client.post("/api/scheduler/caches/does_not_exist/clear")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "cache_unknown"
