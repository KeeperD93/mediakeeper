"""Visibility gates on ``GET /api/portal/achievements/user/{user_id}``.

Aligns the endpoint with ``GET /profiles/by-user-id/{user_id}/public``
so an attacker cannot enumerate the trophy list of a hidden profile or
of the admin account by side-channel.
"""
from __future__ import annotations

import pytest

from core.security import hash_password
from models.user import User
from models.portal.profile import UserProfile


async def _portal_login_admin(client) -> None:
    r = await client.post("/api/auth/portal-login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text


async def _make_user(db_session, *, username: str, role: str, is_public: bool, active: bool):
    user = User(
        username=username,
        hashed_password=hash_password("AnyPassword123!"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role=role,
        is_public=is_public,
        account_active=active,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


@pytest.mark.asyncio
async def test_returns_404_when_target_profile_does_not_exist(client, admin_user):
    await _portal_login_admin(client)
    r = await client.get("/api/portal/achievements/user/99999")
    assert r.status_code == 404
    assert r.json()["detail"] == "profile_not_found"


@pytest.mark.asyncio
async def test_returns_404_when_target_account_is_deactivated(client, admin_user, db_session):
    await _portal_login_admin(client)
    user, _ = await _make_user(
        db_session, username="ghost", role="viewer", is_public=True, active=False,
    )
    r = await client.get(f"/api/portal/achievements/user/{user.id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_returns_404_when_target_is_admin_and_caller_is_someone_else(client, admin_user, db_session):
    """Admin profiles are hidden from non-self lookups so the trophy
    list cannot be used to single them out."""
    await _portal_login_admin(client)
    other_admin, _ = await _make_user(
        db_session, username="other-admin", role="admin", is_public=True, active=True,
    )
    r = await client.get(f"/api/portal/achievements/user/{other_admin.id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_returns_404_when_target_profile_is_private(client, admin_user, db_session):
    """Private profiles return 404 — same shape as missing/admin so the
    caller cannot distinguish the underlying reason."""
    await _portal_login_admin(client)
    user, _ = await _make_user(
        db_session, username="private", role="viewer", is_public=False, active=True,
    )
    r = await client.get(f"/api/portal/achievements/user/{user.id}")
    assert r.status_code == 404
    assert r.json()["detail"] == "profile_not_found"


@pytest.mark.asyncio
async def test_returns_200_when_target_profile_is_public(client, admin_user, db_session):
    await _portal_login_admin(client)
    user, _ = await _make_user(
        db_session, username="public", role="viewer", is_public=True, active=True,
    )
    r = await client.get(f"/api/portal/achievements/user/{user.id}")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    # Only unlocked items survive the filter.
    assert all(a["status"] == "unlocked" for a in body["items"])
