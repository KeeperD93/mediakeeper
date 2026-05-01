"""Tests for the automatic deactivation of expired user accounts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from core.security import hash_password
from models.portal.audit import AdminAuditLog
from models.portal.profile import UserProfile
from models.user import User
from services.portal import admin_users_expiration


def _utc(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


async def _make(db_session, *, username: str, end_days: int | None,
                 emby_id: str | None = "emby-1",
                 emby_disabled: bool | None = False) -> tuple[User, UserProfile]:
    user = User(
        username=username,
        hashed_password=hash_password("dummy"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        account_active=True,
        access_end_date=_utc(end_days) if end_days is not None else None,
        emby_user_id=emby_id,
        emby_is_disabled=emby_disabled,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


@pytest.mark.asyncio
async def test_expire_due_users_deactivates_emby_and_mk(db_session, monkeypatch):
    user, profile = await _make(db_session, username="bob", end_days=-1)
    fake_set = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(admin_users_expiration, "set_emby_user_enabled", fake_set)

    res = await admin_users_expiration.expire_due_users(db_session)

    assert res["processed"] == 1
    assert res["emby_disabled"] == 1
    assert res["errors"] == []

    fake_set.assert_awaited_once()
    _, kwargs = fake_set.await_args
    assert kwargs["enabled"] is False

    await db_session.refresh(profile)
    await db_session.refresh(user)
    assert profile.account_active is False
    assert profile.emby_is_disabled is True
    assert profile.tokens_invalidated_at is not None
    assert user.is_active is False

    audit = (await db_session.execute(
        AdminAuditLog.__table__.select().where(
            AdminAuditLog.target_user_id == user.id
        )
    )).first()
    assert audit is not None
    assert audit.action == "user.access_expired"


@pytest.mark.asyncio
async def test_expire_due_users_skips_future_and_idempotent(db_session, monkeypatch):
    """Future expiry is left alone; a second pass is a no-op."""
    await _make(db_session, username="future", end_days=+30)
    user_past, _ = await _make(db_session, username="past", end_days=-2)

    monkeypatch.setattr(
        admin_users_expiration,
        "set_emby_user_enabled",
        AsyncMock(return_value={"ok": True}),
    )

    first = await admin_users_expiration.expire_due_users(db_session)
    assert first["processed"] == 1

    second = await admin_users_expiration.expire_due_users(db_session)
    assert second["processed"] == 0
    assert second["errors"] == []


@pytest.mark.asyncio
async def test_expire_emby_failure_still_disables_mk(db_session, monkeypatch):
    """Emby unreachable should not block the MediaKeeper-side deactivation."""
    user, profile = await _make(db_session, username="alice", end_days=-1)
    monkeypatch.setattr(
        admin_users_expiration,
        "set_emby_user_enabled",
        AsyncMock(return_value={"error": "network"}),
    )

    res = await admin_users_expiration.expire_due_users(db_session)
    assert res["processed"] == 1
    assert res["emby_disabled"] == 0
    assert res["errors"] and res["errors"][0]["emby_error"] == "network"

    await db_session.refresh(profile)
    await db_session.refresh(user)
    assert profile.account_active is False
    assert user.is_active is False
    # Emby flag stays as-is — admin can retry from the UI
    assert profile.emby_is_disabled is False


@pytest.mark.asyncio
async def test_expire_profile_if_due_login_gate(db_session, monkeypatch):
    user, profile = await _make(db_session, username="late", end_days=-1)
    monkeypatch.setattr(
        admin_users_expiration,
        "set_emby_user_enabled",
        AsyncMock(return_value={"ok": True}),
    )

    triggered = await admin_users_expiration.expire_profile_if_due(
        db_session, profile, user
    )
    assert triggered is True
    await db_session.refresh(profile)
    assert profile.account_active is False


@pytest.mark.asyncio
async def test_expire_profile_if_due_no_window(db_session):
    user, profile = await _make(db_session, username="noend", end_days=None)
    triggered = await admin_users_expiration.expire_profile_if_due(
        db_session, profile, user
    )
    assert triggered is False
    assert profile.account_active is True
