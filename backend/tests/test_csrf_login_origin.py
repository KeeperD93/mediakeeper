"""Origin / Referer guard on the login endpoints.

The login flow bootstraps the CSRF cookie itself, so the double-submit
token cannot be verified on the very first call. To still block
"login-CSRF" (cross-site forced login) we run the Origin / Referer
check on these paths even before any auth cookie exists.

A missing Origin header — typical of curl, mobile SDKs and tests — is
allowed through so legitimate non-browser clients keep working.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_login_rejects_cross_origin_request(raw_client, admin_user):
    """An ``Origin`` header pointing at a foreign site receives 403
    ``csrf_origin_mismatch`` — even without any existing cookie."""
    r = await raw_client.post(
        "/api/auth/login",
        headers={"Origin": "https://evil.example.com"},
        json={"username": "admin", "password": "TestPassword123!"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_origin_mismatch"


@pytest.mark.asyncio
async def test_portal_login_rejects_cross_origin_request(raw_client, admin_user):
    r = await raw_client.post(
        "/api/portal/auth/login",
        headers={"Origin": "https://evil.example.com"},
        json={"username": "admin", "password": "TestPassword123!"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_origin_mismatch"


@pytest.mark.asyncio
async def test_login_accepts_same_origin_request(raw_client, admin_user):
    """Same-origin POST keeps working (the test client base_url is
    ``http://test``)."""
    r = await raw_client.post(
        "/api/auth/login",
        headers={"Origin": "http://test"},
        json={"username": "admin", "password": "TestPassword123!"},
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_login_accepts_request_without_origin_header(raw_client, admin_user):
    """Curl-style clients omit Origin altogether — must keep working
    so internal scripts that hit the API directly are not broken."""
    r = await raw_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "TestPassword123!"},
    )
    assert r.status_code == 200, r.text
