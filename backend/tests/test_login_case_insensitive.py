"""Case-insensitive lookup on /api/auth/login.

The canonical ``users.username`` row is preserved in the DB; only the
lookup is normalised so users can type their handle in any letter case.
The response keeps echoing the canonical form so downstream clients see
exactly what's stored.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
from models.portal.profile import UserProfile
from models.user import User


async def _create_mixed_case_admin(db_session) -> User:
    user = User(
        username="AdminUser",
        hashed_password=hash_password("TestPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_admin_login_lowercase_input_matches_mixed_case_user(
    client, db_session, monkeypatch,
):
    monkeypatch.setenv("MK_ADMIN_USERS", "AdminUser")
    await _create_mixed_case_admin(db_session)

    resp = await client.post(
        "/api/auth/login",
        json={"username": "adminuser", "password": "TestPassword123!"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_admin_login_uppercase_input_matches_mixed_case_user(
    client, db_session, monkeypatch,
):
    monkeypatch.setenv("MK_ADMIN_USERS", "AdminUser")
    await _create_mixed_case_admin(db_session)

    resp = await client.post(
        "/api/auth/login",
        json={"username": "ADMINUSER", "password": "TestPassword123!"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_login_response_returns_canonical_username(
    client, db_session, monkeypatch,
):
    monkeypatch.setenv("MK_ADMIN_USERS", "AdminUser")
    await _create_mixed_case_admin(db_session)

    resp = await client.post(
        "/api/auth/login",
        json={"username": "adminuser", "password": "TestPassword123!"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "AdminUser"


@pytest.mark.asyncio
async def test_portal_login_admin_case_insensitive_routes_to_admin(
    client, db_session, monkeypatch,
):
    """Typing the admin username in any case must still hit the admin
    scope on /portal-login, not cascade to the Emby fallback."""
    monkeypatch.setenv("MK_ADMIN_USERS", "AdminUser")
    await _create_mixed_case_admin(db_session)

    resp = await client.post(
        "/api/auth/portal-login",
        json={"username": "adminuser", "password": "TestPassword123!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["scope"] == "admin"
    assert body["username"] == "AdminUser"


@pytest.mark.asyncio
async def test_emby_auth_lookup_is_case_insensitive(db_session):
    """The Emby cascade (services.portal.emby_auth.authenticate_emby_user)
    must match an imported user regardless of the casing the visitor types.

    Without this, ``/portal-login`` rejects a valid Emby user with
    ``401 invalid_credentials`` whenever the typed casing differs from
    the canonical one stored in the DB — which is exactly what
    motivated this complementary fix to Cycle 1.
    """
    # Imported Emby user — sentinel password, canonical mixed case.
    user = User(
        username="Xyrel",
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name="Xyrel",
        role="viewer",
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()

    # Mock the Emby HTTP client + the active media source so the function
    # never reaches a real Emby instance during the test.
    fake_emby_response = AsyncMock()
    fake_emby_response.status_code = 200
    fake_emby_response.json = lambda: {"User": {"Id": "emby-id-xyz"}}
    fake_client = AsyncMock()
    fake_client.post = AsyncMock(return_value=fake_emby_response)

    with patch(
        "services.portal.emby_auth.get_active_media_source",
        new=AsyncMock(return_value={
            "source": "emby",
            "url": "http://fake-emby.local",
            "api_key": "fake-key",
        }),
    ), patch(
        "services.portal.emby_auth.get_internal_client",
        return_value=fake_client,
    ):
        from services.portal.emby_auth import authenticate_emby_user

        # Lowercase input must still match the canonical "Xyrel".
        result = await authenticate_emby_user(db_session, "xyrel", "any-password")

    assert result is not None, "Lower-case input should match canonical user"
    assert result["user"].username == "Xyrel"
    assert result["user"].id == user.id
