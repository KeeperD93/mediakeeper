"""Users page, Security tab: "Force logout" and "Reset password" end every
session of the target, admin and portal alike, and refuse to target the
acting admin's own account. Synthetic users only."""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from core.security import create_access_token, verify_password
from models.portal.profile import UserProfile
from models.user import User

SECOND_ADMIN = "second_admin"


def _token(username: str, scope: str) -> str:
    return create_access_token({"sub": username, "scope": scope})


async def _own_profile(db_session, admin_user) -> UserProfile:
    profile = UserProfile(
        user_id=admin_user.id, display_name="Admin", role="admin",
        source="local", account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


async def _second_admin(db_session, make_user, monkeypatch) -> tuple[User, UserProfile]:
    monkeypatch.setenv("MK_ADMIN_USERS", f"admin,{SECOND_ADMIN}")
    user = await make_user(SECOND_ADMIN, role="admin")
    profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )).scalar_one()
    profile.source = "local"
    await db_session.commit()
    return user, profile


async def _assert_sessions_revoked(client, admin_token: str, portal_token: str):
    client.cookies.clear()
    client.cookies.set("mk_token", admin_token)
    admin = await client.get("/api/auth/me")
    assert admin.status_code == 401
    assert admin.json()["detail"] == "session_revoked"
    client.cookies.clear()
    client.cookies.set("rq_token", portal_token)
    portal = await client.get("/api/portal/auth/me")
    assert portal.status_code == 401
    assert portal.json()["detail"] == "session_revoked"


@pytest.mark.asyncio
async def test_force_logout_ends_admin_and_portal_sessions(
    client, admin_user, db_session, make_user, monkeypatch,
):
    _, target_profile = await _second_admin(db_session, make_user, monkeypatch)
    admin_token, portal_token = _token(SECOND_ADMIN, "admin"), _token(SECOND_ADMIN, "portal")
    client.cookies.set("mk_token", _token("admin", "admin"))
    await asyncio.sleep(0.05)  # leave the pivot's clock step (Python <= 3.12 on Windows ticks every 15.6 ms)

    resp = await client.post(f"/api/portal/admin/users/{target_profile.id}/force-logout")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    await _assert_sessions_revoked(client, admin_token, portal_token)


@pytest.mark.asyncio
async def test_force_logout_refuses_the_acting_admin_own_account(client, admin_user, db_session):
    profile = await _own_profile(db_session, admin_user)
    client.cookies.set("mk_token", _token("admin", "admin"))

    resp = await client.post(f"/api/portal/admin/users/{profile.id}/force-logout")
    assert resp.status_code == 200
    assert resp.json().get("error") == "self_action_forbidden"

    await db_session.refresh(admin_user)
    await db_session.refresh(profile)
    assert admin_user.tokens_invalidated_at is None
    assert profile.tokens_invalidated_at is None


@pytest.mark.asyncio
async def test_reset_password_ends_admin_and_portal_sessions(
    client, admin_user, db_session, make_user, monkeypatch,
):
    _, target_profile = await _second_admin(db_session, make_user, monkeypatch)
    admin_token, portal_token = _token(SECOND_ADMIN, "admin"), _token(SECOND_ADMIN, "portal")
    client.cookies.set("mk_token", _token("admin", "admin"))

    resp = await client.post(f"/api/portal/admin/users/{target_profile.id}/reset-password")
    assert resp.status_code == 200
    assert resp.json()["password"]

    await _assert_sessions_revoked(client, admin_token, portal_token)


@pytest.mark.asyncio
async def test_reset_password_refuses_the_acting_admin_own_account(client, admin_user, db_session):
    profile = await _own_profile(db_session, admin_user)
    client.cookies.set("mk_token", _token("admin", "admin"))

    resp = await client.post(f"/api/portal/admin/users/{profile.id}/reset-password")
    assert resp.status_code == 200
    assert resp.json().get("error") == "self_action_forbidden"

    await db_session.refresh(admin_user)
    await db_session.refresh(profile)
    assert verify_password("TestPassword123!", admin_user.hashed_password)
    assert admin_user.must_change_password is False
    assert admin_user.tokens_invalidated_at is None
    assert profile.tokens_invalidated_at is None
