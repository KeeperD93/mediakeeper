"""Brute-force tracking must collapse username casing variants.

Before this fix, the per-username failure counter in ``services.security``
keyed off the raw input string. An attacker could alternate
``AdminUser`` / ``ADMINUSER`` / ``adminuser`` / ``AdMiNuSeR`` and stay
under ``FAIL_BLOCK_THRESHOLD`` on every individual key, defeating the
DB-backed lockout. The IP counter still fired from a single source, but
a distributed attack (botnet / proxy rotator) would have bypassed both.

The fix normalises ``req.username`` (strip + lower) before every call
to ``ensure_not_blocked`` / ``record_failure`` / ``record_attempt`` /
``count_recent_failures`` in ``backend.api.auth.login``, so all casing
variants now resolve to a single rate-limit bucket.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.security import SecurityAttempt
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
async def test_failures_under_different_casings_share_one_bucket(
    client, db_session, monkeypatch,
):
    """3 failed attempts using 3 distinct casings must collapse into a
    single per-username row family in ``security_attempts``."""
    monkeypatch.setenv("MK_ADMIN_USERS", "AdminUser")
    await _create_mixed_case_admin(db_session)

    for username_variant in ("AdminUser", "ADMINUSER", "adminuser"):
        resp = await client.post("/api/auth/login", json={
            "username": username_variant,
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401, (
            f"variant {username_variant!r} expected 401, got {resp.status_code}"
        )

    failures = (await db_session.execute(
        select(SecurityAttempt).where(SecurityAttempt.success == 0)
    )).scalars().all()
    assert len(failures) == 3
    assert {row.username for row in failures} == {"adminuser"}, (
        f"all 3 failures must collapse to lowercase 'adminuser', "
        f"got {[row.username for row in failures]}"
    )


@pytest.mark.asyncio
async def test_4th_attempt_is_blocked_regardless_of_casing(
    client, db_session, monkeypatch,
):
    """After 3 failed casing variants, the 4th attempt — even with the
    correct password and yet another casing — must be rate-limited
    (429), not authenticated. Confirms the bucket actually gates the
    follow-up call rather than just being logged."""
    monkeypatch.setenv("MK_ADMIN_USERS", "AdminUser")
    await _create_mixed_case_admin(db_session)

    for username_variant in ("AdminUser", "ADMINUSER", "adminuser"):
        resp = await client.post("/api/auth/login", json={
            "username": username_variant,
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401

    resp = await client.post("/api/auth/login", json={
        "username": "AdMiNuSeR",
        "password": "TestPassword123!",
    })
    assert resp.status_code == 429, (
        f"4th attempt with another casing must be blocked, "
        f"got {resp.status_code} {resp.json()!r}"
    )
