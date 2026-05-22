"""On-disk image proxy cache + Settings → Scheduler integration.

Pins:
- ``_normalize`` rewrites poster_url to the proxy when the flag is ON
  and leaves the raw TMDB URL alone otherwise.
- ``fetch_or_serve`` writes the bytes to disk on a cache miss and
  reads them back on the next call without hitting the network.
- ``clear_cache`` empties the directory + zeros the counters.
- The stats payload matches the shape consumed by the admin readout.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.portal import image_cache


@pytest.fixture(autouse=True)
def _isolated_cache_dir(tmp_path, monkeypatch):
    """Redirect every test to a throwaway directory + reset state."""
    monkeypatch.setattr(image_cache, "CACHE_DIR", tmp_path)
    image_cache._stats["hits"] = 0
    image_cache._stats["misses"] = 0
    # Reset the enable snapshot so each test starts from a known state.
    image_cache._enabled = False
    image_cache._enabled_last_refresh = 0.0
    yield


@pytest.mark.asyncio
async def test_proxied_url_rewrites_tmdb_only():
    """TMDB CDN URLs go through the proxy; anything else stays untouched."""
    tmdb = "https://image.tmdb.org/t/p/w300/abc.jpg"
    assert image_cache.proxied_url(tmdb).startswith("/api/img?u=")
    assert image_cache.proxied_url("https://example.com/x.jpg") == (
        "https://example.com/x.jpg"
    )
    assert image_cache.proxied_url("") == ""


def test_normalize_uses_proxy_when_flag_on():
    """The discover lists ``_normalize`` helper inherits the rewrite."""
    from services.portal.discover_lists import _normalize

    tmdb_raw = {
        "id": 1,
        "media_type": "movie",
        "title": "Test",
        "poster_path": "/abc.jpg",
        "backdrop_path": "/bg.jpg",
    }

    image_cache._enabled = False
    out_off = _normalize(tmdb_raw)
    assert out_off["poster_url"].startswith("https://image.tmdb.org/")
    assert out_off["backdrop"].startswith("https://image.tmdb.org/")

    image_cache._enabled = True
    out_on = _normalize(tmdb_raw)
    assert out_on["poster_url"].startswith("/api/img?u=")
    assert out_on["backdrop"].startswith("/api/img?u=")


@pytest.mark.asyncio
async def test_fetch_writes_to_disk_then_serves_from_cache():
    """First call downloads + writes; second call reads disk only."""
    tmdb_url = "https://image.tmdb.org/t/p/w300/abc.jpg"
    fake_bytes = b"FAKE_PNG_BYTES"

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.content = fake_bytes
    fake_resp.headers = {"content-type": "image/jpeg"}

    fake_client = MagicMock()
    fake_client.get = AsyncMock(return_value=fake_resp)

    with patch(
        "services.portal.image_cache.get_external_client",
        return_value=fake_client,
    ):
        content_first, ct_first = await image_cache.fetch_or_serve(tmdb_url)

    assert content_first == fake_bytes
    assert ct_first == "image/jpeg"
    assert image_cache._stats["misses"] == 1
    assert image_cache._stats["hits"] == 0
    # File must be on disk now.
    cached_path = image_cache._path_for(tmdb_url)
    assert cached_path.exists()
    assert cached_path.read_bytes() == fake_bytes

    # Second call hits the disk without calling the upstream client.
    fake_client.get.reset_mock()
    with patch(
        "services.portal.image_cache.get_external_client",
        return_value=fake_client,
    ):
        content_second, _ = await image_cache.fetch_or_serve(tmdb_url)

    assert content_second == fake_bytes
    fake_client.get.assert_not_called()
    assert image_cache._stats["hits"] == 1
    assert image_cache._stats["misses"] == 1


@pytest.mark.asyncio
async def test_clear_cache_empties_dir_and_resets_counters():
    """After clear, no files, zero hits/misses."""
    tmdb_url = "https://image.tmdb.org/t/p/w300/abc.jpg"
    fake_bytes = b"BYTES"

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.content = fake_bytes
    fake_resp.headers = {"content-type": "image/jpeg"}

    fake_client = MagicMock()
    fake_client.get = AsyncMock(return_value=fake_resp)
    with patch(
        "services.portal.image_cache.get_external_client",
        return_value=fake_client,
    ):
        await image_cache.fetch_or_serve(tmdb_url)

    assert image_cache._stats["misses"] == 1
    assert image_cache._path_for(tmdb_url).exists()

    removed = image_cache.clear_cache()
    assert removed == 1
    assert image_cache._stats["hits"] == 0
    assert image_cache._stats["misses"] == 0
    assert not image_cache._path_for(tmdb_url).exists()


def test_stats_payload_shape():
    """Required keys for the admin readout."""
    stats = image_cache.get_cache_stats()
    for k in ("name", "hits", "misses", "keys", "max_keys", "ttl_seconds", "value_bytes"):
        assert k in stats
    # No size cap, no TTL — these are intentionally null.
    assert stats["max_keys"] is None
    assert stats["ttl_seconds"] is None


@pytest.mark.asyncio
async def test_refresh_flag_caches_for_ttl(db_session, monkeypatch):
    """Reading the toggle twice within the TTL hits the DB once."""
    from services.settings import _kv

    call_count = {"n": 0}
    original_get_setting = _kv.get_setting

    async def counting_get_setting(*args, **kwargs):
        call_count["n"] += 1
        return await original_get_setting(*args, **kwargs)

    monkeypatch.setattr(
        "services.portal.image_cache.get_setting", counting_get_setting
    )

    await image_cache.refresh_enabled_flag(db_session, force=True)
    initial_calls = call_count["n"]
    # Second call within the TTL doesn't query.
    await image_cache.refresh_enabled_flag(db_session)
    assert call_count["n"] == initial_calls
    # Forced refresh always queries.
    await image_cache.refresh_enabled_flag(db_session, force=True)
    assert call_count["n"] == initial_calls + 1


@pytest.mark.asyncio
async def test_proxy_endpoint_rejects_non_tmdb_urls(client):
    """Endpoint guards against SSRF — only TMDB CDN allowed through."""
    resp = await client.get(
        "/api/img?u=https%3A%2F%2Fexample.com%2Fevil.jpg"
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_image_url"


@pytest.mark.asyncio
async def test_proxy_endpoint_rejects_userinfo_bypass(client):
    """``https://image.tmdb.org@evil.com/x`` parses with hostname ``evil.com``."""
    bypass = "https%3A%2F%2Fimage.tmdb.org%40evil.com%2Fposter.jpg"
    resp = await client.get(f"/api/img?u={bypass}")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_image_url"


@pytest.mark.asyncio
async def test_proxy_endpoint_rejects_trailing_dot_subdomain(client):
    """``image.tmdb.org.evil.com`` must not pass the strict host check."""
    bypass = "https%3A%2F%2Fimage.tmdb.org.evil.com%2Fposter.jpg"
    resp = await client.get(f"/api/img?u={bypass}")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_proxy_endpoint_rejects_http_scheme(client):
    """``http://`` is below the bar even for the otherwise-allowed host."""
    resp = await client.get(
        "/api/img?u=http%3A%2F%2Fimage.tmdb.org%2Fposter.jpg"
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_fetch_or_serve_raises_on_non_tmdb_url():
    """Defence in depth: the internal helper refuses non-TMDB URLs too."""
    from core.url_safety import UnsafeOutboundURL

    with pytest.raises(UnsafeOutboundURL) as exc:
        await image_cache.fetch_or_serve("https://evil.example.com/x.jpg")
    assert exc.value.reason == "image_url_rejected"
