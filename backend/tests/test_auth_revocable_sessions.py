"""Coverage for the auth hardening: revocation pivots, scope claims,
WebSocket origin enforcement, and idempotent Emby import."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from sqlalchemy import select

from core.security import (
    create_access_token,
    hash_password,
    is_token_valid_for_revocation_pivot,
)
from models.user import User
from models.portal.profile import UserProfile


# Helper + column default


@pytest.mark.asyncio
async def test_user_tokens_invalidated_at_default_null(db_session):
    user = User(
        username="alice",
        hashed_password=hash_password("Password123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    assert user.tokens_invalidated_at is None


def test_is_token_valid_for_revocation_pivot_no_pivot_keeps_token():
    iat = int(datetime.now(timezone.utc).timestamp())
    assert is_token_valid_for_revocation_pivot(iat, None) is True


def test_is_token_valid_for_revocation_pivot_old_token_rejected():
    pivot = datetime.now(timezone.utc)
    iat = int((pivot - timedelta(minutes=5)).timestamp())
    assert is_token_valid_for_revocation_pivot(iat, pivot) is False


def test_is_token_valid_for_revocation_pivot_new_token_passes():
    pivot = datetime.now(timezone.utc) - timedelta(minutes=5)
    iat = int(datetime.now(timezone.utc).timestamp())
    assert is_token_valid_for_revocation_pivot(iat, pivot) is True


def test_is_token_valid_for_revocation_pivot_compares_fractions_of_a_second():
    pivot = datetime(2026, 1, 1, 12, 0, 0, 500_000, tzinfo=timezone.utc)
    assert is_token_valid_for_revocation_pivot(pivot.timestamp() - 0.2, pivot) is False
    assert is_token_valid_for_revocation_pivot(pivot.timestamp() + 0.2, pivot) is True


def test_tokens_carry_a_sub_second_iat(monkeypatch):
    minted = datetime(2026, 1, 1, 12, 0, 0, 250_000, tzinfo=timezone.utc)

    class _FrozenClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return minted

    monkeypatch.setattr("core.security.datetime", _FrozenClock)
    token = create_access_token({"sub": "alice", "scope": "admin"})
    assert jwt.decode(token, options={"verify_signature": False})["iat"] == minted.timestamp()


# Bearer fallback removed on admin routes


@pytest.mark.asyncio
async def test_admin_bearer_rejected(client, admin_user):
    """A Bearer header alone must no longer authenticate admin routes."""
    token = create_access_token({"sub": admin_user.username, "scope": "admin"})
    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


# Strict scope claim


@pytest.mark.asyncio
async def test_admin_token_without_scope_rejected(client, admin_user):
    """A JWT minted before the scope rollout must no longer be honoured."""
    legacy_token = create_access_token({"sub": admin_user.username})
    client.cookies.set("mk_token", legacy_token)
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_token_with_portal_scope_rejected_on_admin_route(client, admin_user):
    """A portal-scoped JWT must not unlock the admin surface even if dropped
    in the admin cookie."""
    portal_token = create_access_token({"sub": admin_user.username, "scope": "portal"})
    client.cookies.set("mk_token", portal_token)
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_media_proxy_rejects_token_without_scope(client):
    """The media proxy now requires an explicit scope claim on every JWT."""
    legacy_token = create_access_token({"sub": "viewer"})
    client.cookies.set("mk_token", legacy_token)
    with patch(
        "api.core_routes.proxy_image",
        new=AsyncMock(return_value=(b"img", "image/jpeg")),
    ):
        resp = await client.get("/api/emby/image/14437")
    assert resp.status_code == 401


# Change-password revocation


@pytest.mark.asyncio
async def test_change_password_revokes_old_sessions(client, admin_user, db_session):
    """A password change must reject every JWT issued earlier on other
    devices, while the new cookie keeps working."""
    old_token = create_access_token({"sub": admin_user.username, "scope": "admin"})
    client.cookies.set("mk_token", old_token)
    await client.get("/api/auth/me")  # bootstrap CSRF

    change = await client.post(
        "/api/auth/change-password",
        json={
            "current_password": "TestPassword123!",
            "new_password": "BrandNewPassw0rd!",
            "confirm_password": "BrandNewPassw0rd!",
        },
    )
    assert change.status_code == 200
    new_cookie = change.cookies.get("mk_token")
    assert new_cookie and new_cookie != old_token

    # Replay the old token from a "different device".
    client.cookies.clear()
    client.cookies.set("mk_token", old_token)
    client.cookies.set("mk_csrf", "pytest-csrf-token")
    blocked = await client.get(
        "/api/auth/me",
        headers={"X-CSRF-Token": "pytest-csrf-token"},
    )
    assert blocked.status_code == 401
    assert blocked.json()["detail"] == "session_revoked"

    # The freshly-issued token still works.
    client.cookies.clear()
    client.cookies.set("mk_token", new_cookie)
    client.cookies.set("mk_csrf", "pytest-csrf-token")
    keep = await client.get(
        "/api/auth/me",
        headers={"X-CSRF-Token": "pytest-csrf-token"},
    )
    assert keep.status_code == 200


@pytest.mark.asyncio
async def test_change_password_also_ends_the_admin_portal_sessions(client, admin_user, db_session):
    """The admin's portal sessions on other devices end too: ``rq_token`` is
    checked against the profile pivot, not the account one."""
    db_session.add(UserProfile(
        user_id=admin_user.id, display_name="Admin", role="admin", account_active=True,
    ))
    await db_session.commit()
    old_portal_token = create_access_token({"sub": admin_user.username, "scope": "portal"})
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    change = await client.post(
        "/api/auth/change-password",
        json={
            "current_password": "TestPassword123!",
            "new_password": "BrandNewPassw0rd!",
            "confirm_password": "BrandNewPassw0rd!",
        },
    )
    assert change.status_code == 200

    client.cookies.clear()
    client.cookies.set("rq_token", old_portal_token)
    blocked = await client.get("/api/portal/auth/me")
    assert blocked.status_code == 401
    assert blocked.json()["detail"] == "session_revoked"


@pytest.mark.asyncio
async def test_a_cookie_renewed_in_the_same_second_does_not_outlive_a_password_change(
    client, admin_user,
):
    """A stolen cookie renewed just before the change, within the same second,
    must still fall before the new pivot."""
    victim = create_access_token({"sub": admin_user.username, "scope": "admin"})
    await asyncio.sleep(1 - time.time() % 1 + 0.01)  # just past a whole second
    stolen = create_access_token({"sub": admin_user.username, "scope": "admin"})
    client.cookies.set("mk_token", victim)

    change = await client.post(
        "/api/auth/change-password",
        json={
            "current_password": "TestPassword123!",
            "new_password": "BrandNewPassw0rd!",
            "confirm_password": "BrandNewPassw0rd!",
        },
    )
    assert change.status_code == 200

    client.cookies.clear()
    client.cookies.set("mk_token", stolen)
    blocked = await client.get("/api/auth/me")
    assert blocked.status_code == 401
    assert blocked.json()["detail"] == "session_revoked"


@pytest.mark.asyncio
async def test_admin_session_rejected_after_revocation(client, admin_user, db_session):
    """Stamping ``users.tokens_invalidated_at`` directly must lock out
    every JWT issued before that timestamp."""
    token = create_access_token({"sub": admin_user.username, "scope": "admin"})
    client.cookies.set("mk_token", token)
    ok = await client.get("/api/auth/me")
    assert ok.status_code == 200

    user = (await db_session.execute(
        select(User).where(User.username == admin_user.username)
    )).scalar_one()
    user.tokens_invalidated_at = datetime.now(timezone.utc) + timedelta(seconds=1)
    db_session.add(user)
    await db_session.commit()

    blocked = await client.get("/api/auth/me")
    assert blocked.status_code == 401
    assert blocked.json()["detail"] == "session_revoked"


# Server-side revocation on portal logout


@pytest.mark.asyncio
async def test_portal_logout_revokes_server_side(client, admin_user, db_session):
    profile = UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()

    portal_token = create_access_token({"sub": admin_user.username, "scope": "portal"})
    client.cookies.set("rq_token", portal_token)

    resp = await client.post("/api/portal/auth/logout")
    assert resp.status_code == 200

    refreshed = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == admin_user.id)
    )).scalar_one()
    assert refreshed.tokens_invalidated_at is not None


# Daily-digest + changelog/* gated by revocation


@pytest.mark.asyncio
async def test_daily_digest_rejects_after_force_logout(client, admin_user, db_session):
    profile = UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        account_active=True,
        tokens_invalidated_at=datetime.now(timezone.utc) + timedelta(seconds=1),
    )
    db_session.add(profile)
    await db_session.commit()

    portal_token = create_access_token({"sub": admin_user.username, "scope": "portal"})
    client.cookies.set("rq_token", portal_token)

    resp = await client.get("/api/portal/daily-digest")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "session_revoked"


@pytest.mark.asyncio
async def test_changelog_rejects_after_force_logout(client, admin_user, db_session):
    profile = UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        account_active=True,
        tokens_invalidated_at=datetime.now(timezone.utc) + timedelta(seconds=1),
    )
    db_session.add(profile)
    await db_session.commit()

    portal_token = create_access_token({"sub": admin_user.username, "scope": "portal"})
    client.cookies.set("rq_token", portal_token)

    resp = await client.get("/api/portal/changelog/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_changelog_current_remains_public(client):
    """``/current`` is intentionally unauthenticated — version badge."""
    resp = await client.get("/api/portal/changelog/current")
    assert resp.status_code == 200
    assert "version" in resp.json()


# WebSocket origin + revocation sweep


def test_ws_origin_blocked_when_origin_missing(monkeypatch):
    from api.portal.chat import _origin_is_allowed
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example")
    assert _origin_is_allowed(None) is False
    assert _origin_is_allowed("") is False


def test_ws_origin_blocked_when_unknown(monkeypatch):
    from api.portal.chat import _origin_is_allowed
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example")
    assert _origin_is_allowed("https://attacker.example") is False


def test_ws_origin_allowed_for_frontend_origin(monkeypatch):
    from api.portal.chat import _origin_is_allowed
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example,https://lan.example")
    assert _origin_is_allowed("https://app.example") is True
    assert _origin_is_allowed("https://lan.example") is True

@pytest.mark.asyncio
async def test_ws_revocation_kick(db_session, admin_user):
    """``prune_revoked_ws_sessions`` must close sockets whose ``iat`` is
    older than the user's revocation pivot, leaving fresh sockets alone."""
    from api.portal import chat as chat_mod

    profile = UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        account_active=True,
        tokens_invalidated_at=datetime.now(timezone.utc),
    )
    db_session.add(profile)
    await db_session.commit()

    closed_calls: list[int] = []

    class FakeWS:
        def __init__(self, label: int):
            self.label = label

        async def close(self, code: int = 4001):
            closed_calls.append(self.label)

    stale_ws = FakeWS(1)
    fresh_ws = FakeWS(2)
    stale_iat = profile.tokens_invalidated_at - timedelta(minutes=5)
    fresh_iat = profile.tokens_invalidated_at + timedelta(minutes=5)
    chat_mod._ws_rooms.clear()
    chat_mod._ws_rooms[42] = {
        admin_user.id: (stale_ws, stale_iat),
        99: (fresh_ws, fresh_iat),
    }

    closed = await chat_mod.prune_revoked_ws_sessions(db_session)

    assert closed == 1
    assert closed_calls == [1]
    assert admin_user.id not in chat_mod._ws_rooms.get(42, {})
    assert 99 in chat_mod._ws_rooms[42]
    chat_mod._ws_rooms.clear()


# Emby import idempotent under races


@pytest.mark.asyncio
async def test_emby_import_no_double_create(db_session):
    """Two parallel imports targeting the same Emby user must converge to
    a single ``users`` row + a single ``user_profiles`` row, with one
    "created" winner and one "skipped"."""
    from services.portal.admin_users_emby import import_selected_emby_users

    emby_user = {
        "Id": "emby-guid-1",
        "Name": "alice",
        "Policy": {"IsAdministrator": False, "IsDisabled": False},
    }

    with patch(
        "services.portal.admin_users_emby.list_emby_users",
        new=AsyncMock(return_value=[emby_user]),
    ):
        first = await import_selected_emby_users(
            db_session,
            emby_user_ids=["emby-guid-1"],
            admin_user_id=None,
        )
        second = await import_selected_emby_users(
            db_session,
            emby_user_ids=["emby-guid-1"],
            admin_user_id=None,
        )

    assert first.get("ok") and second.get("ok")
    total_created = first.get("created", 0) + second.get("created", 0)
    total_skipped = first.get("skipped", 0) + second.get("skipped", 0)
    assert total_created == 1
    assert total_skipped == 1

    rows = (await db_session.execute(
        select(User).where(User.username == "alice")
    )).scalars().all()
    assert len(rows) == 1

    profile_rows = (await db_session.execute(
        select(UserProfile).where(UserProfile.emby_user_id == "emby-guid-1")
    )).scalars().all()
    assert len(profile_rows) == 1
