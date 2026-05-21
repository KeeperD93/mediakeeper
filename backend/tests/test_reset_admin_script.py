"""Tests for the operator-facing scripts/reset_admin CLI.

The script is the documented recovery path when the bootstrap admin
password printed on first boot is lost (see app_startup._emit_
bootstrap_admin_credentials and docs/operations/admin-recovery.md).
It must:

* Re-hash and persist a fresh random password for the named user.
* Force ``must_change_password=True`` so the next interactive login
  still requires the operator to pick a real password.
* Stamp ``tokens_invalidated_at`` so every JWT issued under the old
  credentials is treated as revoked by the auth middleware.
* Print the new credentials on stdout once and never log them.
* Refuse to reset a non-admin account and exit with a distinct code.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from core.security import hash_password, verify_password
from models.user import User
from scripts import reset_admin as reset_admin_module


def _shared_session_factory(session):
    """Return a context-manager factory that yields ``session`` and does
    not close it on exit — the test's ``db_session`` fixture owns the
    lifecycle. Required because ``:memory:`` SQLite gives every fresh
    pool connection its own empty DB."""

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *exc):
            return False

    return _Ctx


@pytest_asyncio.fixture
async def seeded_admin(db_session):
    user = User(
        username="admin",
        hashed_password=hash_password("OldPasswordABC123!"),
        is_active=True,
        must_change_password=False,
        tokens_invalidated_at=None,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def seeded_portal_user(db_session):
    user = User(
        username="alice",
        hashed_password=hash_password("PortalPwd123!"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_resets_password_and_invalidates_tokens(
    seeded_admin, db_session, capsys, monkeypatch
):
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")
    before = datetime.now(timezone.utc)

    exit_code = await reset_admin_module._reset(
        "admin", session_factory=_shared_session_factory(db_session)
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "ADMIN PASSWORD RESET" in captured.out
    assert "Username: admin" in captured.out
    assert "Password: " in captured.out

    password_line = next(
        line for line in captured.out.splitlines() if line.strip().startswith("Password:")
    )
    new_password = password_line.split("Password:", 1)[1].strip()
    assert len(new_password) >= 16

    await db_session.refresh(seeded_admin)
    assert verify_password(new_password, seeded_admin.hashed_password)
    assert not verify_password("OldPasswordABC123!", seeded_admin.hashed_password)
    assert seeded_admin.must_change_password is True
    assert seeded_admin.tokens_invalidated_at is not None
    # SQLite drops tzinfo on round-trip even when the column is declared
    # DateTime(timezone=True). Normalise before the chronology check.
    ti = seeded_admin.tokens_invalidated_at
    if ti.tzinfo is None:
        ti = ti.replace(tzinfo=timezone.utc)
    assert ti >= before


@pytest.mark.asyncio
async def test_returns_1_when_user_missing(db_session, capsys):
    exit_code = await reset_admin_module._reset(
        "ghost", session_factory=_shared_session_factory(db_session)
    )
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "user not found" in err


@pytest.mark.asyncio
async def test_refuses_to_reset_non_admin_user(
    seeded_portal_user, db_session, capsys, monkeypatch
):
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")  # alice is not in the allow-list

    exit_code = await reset_admin_module._reset(
        "alice", session_factory=_shared_session_factory(db_session)
    )
    assert exit_code == 2
    err = capsys.readouterr().err
    assert "not a backoffice admin" in err

    await db_session.refresh(seeded_portal_user)
    assert verify_password("PortalPwd123!", seeded_portal_user.hashed_password)
