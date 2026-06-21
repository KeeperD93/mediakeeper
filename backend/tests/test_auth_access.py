"""Tests for protected routes: /me, backoffice, Emby image proxy."""
from unittest.mock import AsyncMock, patch

import pytest

from core.security import create_access_token, hash_password
from models.user import User
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token


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
async def test_emby_image_proxy_accepts_active_admin_cookie(client, admin_user):
    """The image proxy accepts a valid admin cookie backed by an active,
    non-revoked account (#389)."""
    token = create_access_token({"sub": admin_user.username, "scope": "admin"})
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
async def test_emby_user_image_missing_returns_204(client, admin_user):
    """Une absence d'avatar Emby ne doit pas polluer le frontend with une 404."""
    token = create_access_token({"sub": admin_user.username, "scope": "admin"})
    client.cookies.set("mk_token", token)

    with patch("api.core_routes.proxy_user_image", new=AsyncMock(return_value=None)):
        resp = await client.get("/api/emby/user-image/abc123")

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_emby_user_image_advertises_short_cache(client, admin_user):
    """The avatar response must opt into a short browser cache so a user
    updating their Emby photo sees the new portrait within minutes — not
    pinned by an aggressive ``max-age`` for a week."""
    token = create_access_token({"sub": admin_user.username, "scope": "admin"})
    client.cookies.set("mk_token", token)

    with patch(
        "api.core_routes.proxy_user_image",
        new=AsyncMock(return_value=(b"\x89PNG\r\n\x1a\n", "image/png")),
    ):
        resp = await client.get("/api/emby/user-image/abc123")

    assert resp.status_code == 200
    assert resp.headers.get("cache-control") == "private, max-age=300"


@pytest.mark.asyncio
async def test_emby_image_proxy_rejects_deactivated_account(client, admin_user, db_session):
    """A deactivated admin's still-valid JWT stops loading images at once,
    instead of riding the token to its natural expiry (#389)."""
    token = create_access_token({"sub": admin_user.username, "scope": "admin"})
    client.cookies.set("mk_token", token)
    admin_user.is_active = False
    db_session.add(admin_user)
    await db_session.commit()

    resp = await client.get("/api/emby/image/14437")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_emby_image_proxy_accepts_active_portal_user(client, db_session):
    """A valid portal session loads images through the portal branch (#389)."""
    user, _ = await make_portal_user(db_session, username="poster_viewer", role="viewer")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    with patch("api.core_routes.proxy_image", new=AsyncMock(return_value=(b"img", "image/jpeg"))):
        resp = await client.get("/api/emby/image/14437")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_emby_image_proxy_rejects_disabled_portal_profile(client, db_session):
    """A disabled portal profile can no longer ride the image proxy (#389)."""
    user, profile = await make_portal_user(db_session, username="poster_disabled", role="viewer")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    profile.account_active = False
    db_session.add(profile)
    await db_session.commit()

    resp = await client.get("/api/emby/image/14437")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_emby_image_proxy_rejects_pre_pivot_admin_token(client, admin_user, db_session):
    """A JWT issued before the force-logout pivot is rejected on the image
    proxy — not only the deactivation case (#389 revocation headline)."""
    from datetime import datetime, timedelta, timezone

    token = create_access_token({"sub": admin_user.username, "scope": "admin"})
    client.cookies.set("mk_token", token)
    # Pivot in the (near) future so the just-issued token's iat predates it.
    admin_user.tokens_invalidated_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    db_session.add(admin_user)
    await db_session.commit()

    resp = await client.get("/api/emby/image/14437")
    assert resp.status_code == 401
