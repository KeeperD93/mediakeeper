"""``GET /api/img`` is exempt from rate limiting.

The image proxy serves public, SSRF-guarded TMDB CDN bytes cached browser-side
for 7 days, and the Portal Home alone renders 100+ tiles per view. It is
exempt from the global ``120/minute`` default (``@limiter.exempt``) so a single
page load cannot exhaust the per-IP budget and 429 the tail of its tiles — the
slowapi middleware applies that default to every route, and a per-route
``@limiter.limit`` only stacks on top, it cannot raise the cap. This test pins
the contract: a burst far above the default must never surface a 429.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

_TMDB_URL = "https://image.tmdb.org/t/p/w500/contract-pin.jpg"
_FAKE_BYTES = (b"\xff\xd8\xff\xe0fake", "image/jpeg")


@pytest.mark.asyncio
async def test_image_proxy_is_exempt_from_rate_limiting(client):
    """A burst well above the global 120/min default must all return 200 —
    the proxy is exempt, so no request is ever throttled."""
    seen = []
    with patch(
        "services.portal.image_cache.fetch_or_serve",
        new_callable=AsyncMock,
        return_value=_FAKE_BYTES,
    ):
        for _ in range(400):
            r = await client.get("/api/img", params={"u": _TMDB_URL})
            seen.append(r.status_code)
    assert 429 not in seen, (
        f"image proxy must be exempt from rate limiting, saw: {sorted(set(seen))}"
    )
    assert set(seen) == {200}, f"all calls should return 200, saw: {sorted(set(seen))}"
