"""``GET /api/portal/profiles/by-user-id/{user_id}/public`` must not
distinguish 403 (private) from 404 (missing) when the caller is not
the profile owner. Returning the same 404 in both cases prevents
existence enumeration through the response shape.
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


async def _make_user(db_session, *, username: str, is_public: bool):
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
        role="viewer",
        is_public=is_public,
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


@pytest.mark.asyncio
async def test_private_profile_returns_404_not_403(client, admin_user, db_session):
    await _portal_login_admin(client)
    user, _ = await _make_user(db_session, username="private", is_public=False)
    r = await client.get(f"/api/portal/profiles/by-user-id/{user.id}/public")
    assert r.status_code == 404
    assert r.json()["detail"] == "profile_not_found"


@pytest.mark.asyncio
async def test_missing_profile_returns_same_404(client, admin_user, db_session):
    await _portal_login_admin(client)
    r = await client.get("/api/portal/profiles/by-user-id/99999/public")
    assert r.status_code == 404
    assert r.json()["detail"] == "profile_not_found"


@pytest.mark.asyncio
async def test_public_profile_still_returns_200(client, admin_user, db_session):
    await _portal_login_admin(client)
    user, _ = await _make_user(db_session, username="public", is_public=True)
    r = await client.get(f"/api/portal/profiles/by-user-id/{user.id}/public")
    assert r.status_code == 200
