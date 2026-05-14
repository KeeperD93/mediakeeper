"""Rate-limit contract on ``POST /api/portal/availability``.

The Portal Home fans out ~13 carousels and each one calls availability
when its data resolves — even with frontend coalescing in place, a tab
that loads twice in a minute can easily hit double-digit calls. The
historical ``30/minute`` cap saturated under normal use and triggered
a stack of "Too many attempts" toasts.

The new ``120/minute`` cap leaves a comfortable headroom for that
usage pattern while still throttling a runaway loop. This test pins
that contract so a future change to the decorator cannot silently
revert to the saturating value.
"""
from __future__ import annotations

import pytest

from services.portal.profiles import get_or_create_profile


async def _portal_login(client) -> None:
    r = await client.post("/api/auth/portal-login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_availability_allows_100_calls_per_minute(client, admin_user, db_session):
    """Sanity floor — the limit must accept at least the burst the Home
    page can plausibly emit (carousel count × a couple of refreshes).
    With the historical ``30/minute`` cap, this loop tripped on call 31."""
    await _portal_login(client)
    await get_or_create_profile(db_session, admin_user)

    for i in range(100):
        r = await client.post("/api/portal/availability", json={
            "items": [{"tmdb_id": 162617, "media_type": "movie"}],
        })
        assert r.status_code == 200, f"call #{i + 1} unexpectedly returned {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_availability_throttles_beyond_120_per_minute(client, admin_user, db_session):
    """Past the configured ceiling the endpoint must surface a 429 —
    the limiter is still active, just dimensioned for batched reads."""
    await _portal_login(client)
    await get_or_create_profile(db_session, admin_user)

    seen = []
    for _ in range(125):
        r = await client.post("/api/portal/availability", json={
            "items": [{"tmdb_id": 162617, "media_type": "movie"}],
        })
        seen.append(r.status_code)

    assert 429 in seen, f"expected a 429 within 125 calls, saw status counts: {sorted(set(seen))}"
