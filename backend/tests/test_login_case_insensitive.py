"""Case-insensitive lookup on /api/auth/login.

The canonical ``users.username`` row is preserved in the DB; only the
lookup is normalised so users can type their handle in any letter case.
The response keeps echoing the canonical form so downstream clients see
exactly what's stored.
"""
from __future__ import annotations

import pytest

from core.security import hash_password
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
