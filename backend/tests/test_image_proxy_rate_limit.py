"""Rate-limit contract on ``GET /api/img``.

The Portal Home renders ~130 image tiles on first paint. Under the
slowapi global default (``120/minute`` per IP), the tail of that
burst returned 429s and broke the badge UI until the in-memory
bucket recovered. The image proxy now carves out a dedicated
``1800/minute`` per-IP ceiling — well above the legitimate burst,
still throttling a runaway hammer loop. This test pins the contract
so a future change cannot silently revert the proxy to the shared
default.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

_TMDB_URL = "https://image.tmdb.org/t/p/w500/contract-pin.jpg"
_FAKE_BYTES = (b"\xff\xd8\xff\xe0fake", "image/jpeg")


@pytest.mark.asyncio
async def test_image_proxy_allows_300_calls_per_minute(client):
    """Sanity floor — accept at least the Home's first-paint burst.

    300 well exceeds the 120/min global default and stays well below
    the dedicated 1800/min cap; every call must return 200.
    """
    with patch(
        "services.portal.image_cache.fetch_or_serve",
        new_callable=AsyncMock,
        return_value=_FAKE_BYTES,
    ):
        for i in range(300):
            r = await client.get("/api/img", params={"u": _TMDB_URL})
            assert r.status_code == 200, (
                f"call #{i + 1} unexpectedly returned {r.status_code}: {r.text}"
            )


@pytest.mark.asyncio
async def test_image_proxy_throttles_beyond_1800_per_minute(client):
    """Past the configured ceiling the endpoint must surface a 429 —
    the limiter is still active, just dimensioned for image bursts.
    """
    seen = []
    with patch(
        "services.portal.image_cache.fetch_or_serve",
        new_callable=AsyncMock,
        return_value=_FAKE_BYTES,
    ):
        for _ in range(1820):
            r = await client.get("/api/img", params={"u": _TMDB_URL})
            seen.append(r.status_code)
    assert 429 in seen, (
        f"expected a 429 within 1820 calls, saw status counts: {sorted(set(seen))}"
    )
