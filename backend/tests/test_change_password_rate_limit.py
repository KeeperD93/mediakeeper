"""Rate-limit + brute-force counter tests for /api/auth/change-password.

Two layers must be wired in concert:

* slowapi ``@limiter.limit("5/minute", key_func=admin_user_or_ip_key)``
  — capped per authenticated username so a router-NAT'd household does
  not throttle each other.
* DB ``SecurityAttempt`` rows on scope ``admin_password`` so the
  security dashboard surfaces password-change abuse alongside login
  abuse, and the existing auto-block kicks in after 3 failed attempts.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.security import SecurityAttempt
from models.user import User


async def _login(client) -> None:
    """Open a backoffice session so the change-password endpoint sees an auth cookie."""
    r = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_change_password_records_failure_on_wrong_current(client, admin_user, db_session):
    """A wrong ``current_password`` writes a SecurityAttempt row scoped
    ``admin_password`` so admins can investigate abuse from the dashboard."""
    await _login(client)

    r = await client.post("/api/auth/change-password", json={
        "current_password": "WrongPassword!",
        "new_password": "NewPassword123!",
        "confirm_password": "NewPassword123!",
    })
    assert r.status_code == 400
    assert r.json()["detail"] == "current_password_invalid"

    rows = (await db_session.execute(
        select(SecurityAttempt).where(SecurityAttempt.scope == "admin_password")
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].success == 0
    assert rows[0].username == "admin"


@pytest.mark.asyncio
async def test_change_password_records_success_on_valid_swap(client, admin_user, db_session):
    """A successful change writes a single ``success=1`` row so the
    dashboard can show the legitimate event next to a streak of
    failures (helps the admin spot a recovered brute-force)."""
    await _login(client)

    r = await client.post("/api/auth/change-password", json={
        "current_password": "TestPassword123!",
        "new_password": "RotatedPassword456!",
        "confirm_password": "RotatedPassword456!",
    })
    assert r.status_code == 200, r.text

    rows = (await db_session.execute(
        select(SecurityAttempt).where(SecurityAttempt.scope == "admin_password")
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].success == 1
    assert rows[0].username == "admin"


@pytest.mark.asyncio
async def test_change_password_tracks_the_lower_cased_name(client, db_session, monkeypatch):
    """An account created with capitals is tracked under its lower-cased name, like
    the sign-in routes, so its blocks and attempts carry one form of the name."""
    monkeypatch.setenv("MK_ADMIN_USERS", "AdminUser")
    db_session.add(User(
        username="AdminUser",
        hashed_password=hash_password("TestPassword123!"),
        is_active=True,
        must_change_password=False,
    ))
    await db_session.commit()
    r = await client.post("/api/auth/login", json={"username": "adminuser", "password": "TestPassword123!"})
    assert r.status_code == 200, r.text

    statuses = []
    for current in ("WrongPassword!", "TestPassword123!"):
        r = await client.post("/api/auth/change-password", json={
            "current_password": current,
            "new_password": "RotatedPassword456!",
            "confirm_password": "RotatedPassword456!",
        })
        statuses.append(r.status_code)
    assert statuses == [400, 200]

    rows = (await db_session.execute(
        select(SecurityAttempt.username, SecurityAttempt.success)
        .where(SecurityAttempt.scope == "admin_password")
        .order_by(SecurityAttempt.id)
    )).all()
    assert [tuple(row) for row in rows] == [("adminuser", 0), ("adminuser", 1)]


@pytest.mark.asyncio
async def test_change_password_auto_blocks_after_three_failures(client, admin_user, db_session):
    """After ``FAIL_BLOCK_THRESHOLD`` consecutive wrong attempts the
    next call returns 429 ``login_blocked`` from ``ensure_not_blocked``
    — independent from the slowapi 5/min cap (DB block survives a
    process restart, slowapi memory does not)."""
    await _login(client)

    for _ in range(3):
        r = await client.post("/api/auth/change-password", json={
            "current_password": "WrongPassword!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        })
        assert r.status_code == 400

    r = await client.post("/api/auth/change-password", json={
        "current_password": "TestPassword123!",
        "new_password": "RotatedPassword456!",
        "confirm_password": "RotatedPassword456!",
    })
    assert r.status_code == 429
    assert r.json()["detail"] == "login_blocked"


@pytest.mark.asyncio
async def test_change_password_slowapi_caps_at_five_per_minute(client, admin_user):
    """A mismatch records no failure, so only slowapi can answer 429 here. Its
    429 keeps the plain body, with no code and no wait: the shared toast speaks
    for it, unlike the sign-in routes."""
    await _login(client)

    seen = []
    for _ in range(6):
        r = await client.post("/api/auth/change-password", json={
            "current_password": "TestPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "OtherPassword123!",
        })
        seen.append(r.status_code)

    assert seen == [400] * 5 + [429]
    assert "detail" not in r.json()
    assert "Retry-After" not in r.headers
