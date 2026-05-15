"""Tests for `services.tmdb.get_meta_cached`.

The function backfills runtime + year for Top 20 cards from TMDB and
caches the result in-process for 24 h. These tests pin its contract:
shape per media type, invalid media-type guard, cache reuse within the
TTL window, and graceful degradation on transport / HTTP failures.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import services.tmdb as tmdb_mod
from services.tmdb import get_meta_cached


# ── Helpers ─────────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


def _make_client(response_or_exc) -> AsyncMock:
    """Build an AsyncMock client whose `.get(...)` returns the given
    response, or raises when the value is an Exception instance."""
    client = AsyncMock()
    if isinstance(response_or_exc, Exception):
        client.get = AsyncMock(side_effect=response_or_exc)
    else:
        client.get = AsyncMock(return_value=response_or_exc)
    return client


@pytest.fixture(autouse=True)
def _reset_meta_cache():
    """Drop the module-level meta cache between tests so cache-hit
    expectations cannot bleed across cases."""
    tmdb_mod._meta_cache.clear()
    yield
    tmdb_mod._meta_cache.clear()


@pytest.fixture
def fake_db():
    """Sentinel value standing in for an `AsyncSession` — `get_meta_cached`
    only forwards it to `_get_tmdb_key`, which we patch as a no-op."""
    return MagicMock(name="fake_db")


# ── Cases ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_movie_returns_runtime_and_year(fake_db):
    """A movie payload exposes runtime + release_date — both surface."""
    client = _make_client(
        _FakeResponse(200, {"runtime": 105, "release_date": "2024-03-15"})
    )
    with patch("services.tmdb.get_external_client", return_value=client), \
         patch("services.tmdb._get_tmdb_key", new=AsyncMock(return_value="fake-key")):
        meta = await get_meta_cached(123, "movie", fake_db)
    assert meta == {"runtime": 105, "year": "2024"}
    assert client.get.await_count == 1


@pytest.mark.asyncio
async def test_series_uses_episode_run_time(fake_db):
    """TV payloads expose episode_run_time[0] + first_air_date."""
    client = _make_client(
        _FakeResponse(200, {"episode_run_time": [50], "first_air_date": "2023-11-02"})
    )
    with patch("services.tmdb.get_external_client", return_value=client), \
         patch("services.tmdb._get_tmdb_key", new=AsyncMock(return_value="fake-key")):
        meta = await get_meta_cached(456, "tv", fake_db)
    assert meta == {"runtime": 50, "year": "2023"}


@pytest.mark.asyncio
async def test_invalid_media_type_returns_empty_dict(fake_db):
    """Anything other than movie/tv short-circuits without an HTTP call."""
    client = _make_client(_FakeResponse(200, {"runtime": 90}))
    with patch("services.tmdb.get_external_client", return_value=client) as gec, \
         patch("services.tmdb._get_tmdb_key", new=AsyncMock(return_value="fake-key")):
        meta = await get_meta_cached(1, "person", fake_db)
    assert meta == {}
    # No call to the HTTP client whatsoever — guard is the very first
    # statement in the function.
    gec.assert_not_called()


@pytest.mark.asyncio
async def test_cache_hit_within_ttl(fake_db):
    """The second call on the same key reuses the cache (one HTTP call)."""
    client = _make_client(
        _FakeResponse(200, {"runtime": 120, "release_date": "2022-05-01"})
    )
    with patch("services.tmdb.get_external_client", return_value=client), \
         patch("services.tmdb._get_tmdb_key", new=AsyncMock(return_value="fake-key")):
        first = await get_meta_cached(42, "movie", fake_db)
        second = await get_meta_cached(42, "movie", fake_db)
    assert first == second == {"runtime": 120, "year": "2022"}
    assert client.get.await_count == 1


@pytest.mark.asyncio
async def test_failure_returns_empty_dict_without_raising(fake_db):
    """Transport errors are swallowed: the caller stays renderable."""
    client = _make_client(Exception("network down"))
    with patch("services.tmdb.get_external_client", return_value=client), \
         patch("services.tmdb._get_tmdb_key", new=AsyncMock(return_value="fake-key")):
        meta = await get_meta_cached(7, "movie", fake_db)
    assert meta == {}
    # Nothing got cached so the next call would retry from scratch.
    assert (7, "movie") not in tmdb_mod._meta_cache


@pytest.mark.asyncio
async def test_http_non_200_returns_empty_dict(fake_db):
    """A 503 (or any non-200) yields an empty dict, never cached."""
    client = _make_client(_FakeResponse(503))
    with patch("services.tmdb.get_external_client", return_value=client), \
         patch("services.tmdb._get_tmdb_key", new=AsyncMock(return_value="fake-key")):
        meta = await get_meta_cached(9, "movie", fake_db)
    assert meta == {}
    assert (9, "movie") not in tmdb_mod._meta_cache
