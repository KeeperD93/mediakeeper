"""Rate-limit contract on ``POST /api/portal/availability``.

The Portal Home fans out ~13 carousels and infinite-scroll discover keeps
firing batched availability checks as the user browses. Even with frontend
coalescing, an active browse easily exceeds the old ``120/minute`` cap and
stacked "Too many attempts" toasts.

The cap is now ``3600/minute`` (per portal-user / IP): a high ceiling that
clears legitimate browsing while still bounding a runaway loop. These tests
pin that contract so a future change cannot silently revert it (or drop the
decorator, falling back to the global 120 default).
"""
from __future__ import annotations

import pytest

from services.portal.profiles import get_or_create_profile

_AVAILABILITY_ROUTE = "api.portal.availability.check_availability"


async def _portal_login(client) -> None:
    r = await client.post("/api/auth/portal-login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_availability_allows_large_browsing_burst(client, admin_user, db_session):
    """The raised ceiling must accept a burst far above the old 120/min cap —
    a fast browse legitimately exceeds it. Under the previous 120/min limit
    this loop tripped on call 121; 200 calls must now all succeed."""
    await _portal_login(client)
    await get_or_create_profile(db_session, admin_user)

    for i in range(200):
        r = await client.post("/api/portal/availability", json={
            "items": [{"tmdb_id": 162617, "media_type": "movie"}],
        })
        assert r.status_code == 200, f"call #{i + 1} returned {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_availability_limit_is_3600_per_minute():
    """Pin the exact configured ceiling. A behavioural upper-bound test would
    need 3601 calls, so introspect the limiter instead — this also guards
    against the route being accidentally made exempt or dropped to the default."""
    import main as main_module

    limits = main_module.limiter._route_limits.get(_AVAILABILITY_ROUTE)
    assert limits, "availability route has no per-route limit configured"
    rate = limits[0].limit
    assert rate.amount == 3600, f"expected 3600/min, got {rate.amount}"
    assert rate.GRANULARITY.seconds == 60
