"""Slowapi 5/min/IP cap on the login endpoints.

The DB-backed brute-force counter (``services.security``) already
auto-blocks after 3 failed attempts, but it only fires on **failed**
calls. Slowapi sits one layer above and caps the **total** call rate
per IP — protects against credential stuffing campaigns that mix
correct + wrong credentials to evade the failure-only counter.

Every call here succeeds, so no block can answer 429 in the limiter's place.
"""
from __future__ import annotations

import pytest

MAX_WAIT_SECONDS = 60


@pytest.mark.parametrize("path", ["/api/auth/login", "/api/auth/portal-login"])
@pytest.mark.asyncio
async def test_sign_in_routes_cap_at_five_per_minute_and_say_how_long(client, admin_user, path):
    """The 6th call from one IP within a minute is refused even though the first
    5 succeed, with the limit's own code and the wait the sign-in page shows."""
    answers = [
        await client.post(path, json={"username": "admin", "password": "TestPassword123!"})
        for _ in range(6)
    ]

    assert [a.status_code for a in answers] == [200] * 5 + [429]
    refused = answers[-1]
    assert refused.json() == {"detail": "login_rate_limited"}
    assert 1 <= int(refused.headers["Retry-After"]) <= MAX_WAIT_SECONDS
    # Defence-in-depth: this 429 still carries the security headers.
    assert refused.headers.get("X-Content-Type-Options") == "nosniff"


@pytest.mark.asyncio
async def test_the_wait_counts_down_to_the_end_of_the_window(client, admin_user, monkeypatch):
    """The wait is what is left of the minute, never a flat 60 s."""
    from core import rate_limit

    for _ in range(5):
        await client.post("/api/auth/login", json={"username": "admin", "password": "TestPassword123!"})
    now = rate_limit.time.time()
    monkeypatch.setattr(rate_limit.time, "time", lambda: now + 45)

    refused = await client.post("/api/auth/login", json={"username": "admin", "password": "TestPassword123!"})

    assert refused.status_code == 429
    assert 1 <= int(refused.headers["Retry-After"]) <= 15
