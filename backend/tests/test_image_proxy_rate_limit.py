"""``GET /api/img`` keeps its own high per-IP limit, above the global default.

The image proxy serves public, SSRF-guarded TMDB CDN bytes cached browser-side
for 7 days, and the Portal Home alone renders 100+ tiles per view. It carries a
per-route ``@limiter.limit("1800/minute")`` that overrides the global
``120/minute`` default, so a single page load cannot 429 the tail of its tiles.
This test pins that contract: a burst far above the 120 default (but under the
route's own cap) must never surface a 429.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

_TMDB_URL = "https://image.tmdb.org/t/p/w500/contract-pin.jpg"
_FAKE_BYTES = (b"\xff\xd8\xff\xe0fake", "image/jpeg")


@pytest.mark.asyncio
async def test_image_proxy_burst_above_default_is_not_throttled(client):
    """A 300-call burst (>120 default, <1800 route cap) returns all 200 — the
    route's own limit overrides the default, so no tile is throttled."""
    seen = []
    with patch(
        "services.portal.image_cache.fetch_or_serve",
        new_callable=AsyncMock,
        return_value=_FAKE_BYTES,
    ):
        for _ in range(300):
            r = await client.get("/api/img", params={"u": _TMDB_URL})
            seen.append(r.status_code)
    assert 429 not in seen, (
        f"a 300-burst above the 120 default must not 429, saw: {sorted(set(seen))}"
    )
    assert set(seen) == {200}, f"all calls should return 200, saw: {sorted(set(seen))}"
