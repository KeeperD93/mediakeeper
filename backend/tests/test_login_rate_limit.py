"""Slowapi 5/min/IP cap on the login endpoints.

The DB-backed brute-force counter (``services.security``) already
auto-blocks after 3 failed attempts, but it only fires on **failed**
calls. Slowapi sits one layer above and caps the **total** call rate
per IP — protects against credential stuffing campaigns that mix
correct + wrong credentials to evade the failure-only counter.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_login_caps_at_five_per_minute(client, admin_user):
    """The 6th call from one IP within a minute returns 429 even when the
    first 5 succeed (no DB block triggered)."""
    seen_codes: list[int] = []
    for _ in range(7):
        r = await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "TestPassword123!",
        })
        seen_codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 200 in seen_codes
    assert 429 in seen_codes, f"expected slowapi 429 within 7 calls, saw {seen_codes}"


@pytest.mark.asyncio
async def test_portal_login_admin_endpoint_caps_at_five_per_minute(client, admin_user):
    """Same 5/min cap on /api/auth/portal-login (cascade login). The limit
    is per route, so the branch taken does not matter."""
    seen_codes: list[int] = []
    for _ in range(7):
        r = await client.post("/api/auth/portal-login", json={
            "username": "admin",
            "password": "TestPassword123!",
        })
        seen_codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in seen_codes, f"expected slowapi 429 within 7 calls, saw {seen_codes}"
