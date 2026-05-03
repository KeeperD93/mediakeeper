"""Tests for protected routes: /me, backoffice, Emby image proxy."""
from unittest.mock import AsyncMock, patch

import pytest

from core.security import create_access_token, hash_password
from models.user import User


@pytest.mark.asyncio
async def test_non_admin_token_cannot_access_backoffice(client, db_session):
    """A valid JWT outside the admin allowlist must not grant backoffice access."""
    db_session.add(User(
        username="viewer",
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    ))
    await db_session.commit()

    token = create_access_token({"sub": "viewer", "scope": "admin"})
    client.cookies.set("mk_token", token)
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_without_token(client):
    """GET /api/auth/me without token doit returnr 401."""
    resp = await client.get("/api/auth/me")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_protected_route_without_auth(client):
    """Protected routes without a token must return 401/403."""
    routes = [
        "/api/config",
        "/api/stats/system",
        "/api/settings/tools",
    ]
    for route in routes:
        resp = await client.get(route)
        assert resp.status_code in (401, 403), f"{route} returned {resp.status_code}"


@pytest.mark.asyncio
async def test_emby_image_proxy_accepts_valid_cookie_without_db_lookup(client):
    """The image proxy must accept a valid JWT without requiring a DB user per poster."""
    token = create_access_token({"sub": "viewer", "scope": "admin"})
    client.cookies.set("mk_token", token)

    with patch("api.core_routes.proxy_image", new=AsyncMock(return_value=(b"img", "image/jpeg"))):
        resp = await client.get("/api/emby/image/14437")

    assert resp.status_code == 200
    assert resp.content == b"img"
    assert resp.headers["content-type"].startswith("image/jpeg")


@pytest.mark.asyncio
async def test_emby_image_proxy_rejects_query_token_without_cookie(client):
    """JWTs passed in the query string must no longer authenticate image proxies."""
    token = create_access_token({"sub": "viewer", "scope": "admin"})
    resp = await client.get(f"/api/emby/image/14437?token={token}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_emby_user_image_missing_returns_204(client):
    """Une absence d'avatar Emby ne doit pas polluer le frontend with une 404."""
    token = create_access_token({"sub": "admin", "scope": "admin"})
    client.cookies.set("mk_token", token)

    with patch("api.core_routes.proxy_user_image", new=AsyncMock(return_value=None)):
        resp = await client.get("/api/emby/user-image/abc123")

    assert resp.status_code == 204
