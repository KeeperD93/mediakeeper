"""Hash/verify hardening for bcrypt 5 (>72-byte UTF-8 limit).

bcrypt 5 raises ``ValueError`` on inputs longer than 72 bytes instead of
silently truncating, so every hash/verify call must defend against it
or schema-validate up front. The tests below pin both layers:

* :mod:`core.security` returns / raises a controlled error.
* The auth API never produces a 500 from user-supplied credentials.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from core.security import (
    MAX_BCRYPT_PASSWORD_BYTES,
    PasswordTooLongError,
    hash_password,
    verify_password,
)
from models.user import User


def test_hash_then_verify_roundtrip():
    h = hash_password("SafePassword123!")
    assert verify_password("SafePassword123!", h) is True
    assert verify_password("SafePassword124!", h) is False


def test_hash_password_at_72_byte_boundary():
    plain = "a" * MAX_BCRYPT_PASSWORD_BYTES
    h = hash_password(plain)
    assert verify_password(plain, h) is True


def test_hash_password_raises_typed_error_above_72_bytes():
    with pytest.raises(PasswordTooLongError) as excinfo:
        hash_password("a" * (MAX_BCRYPT_PASSWORD_BYTES + 1))
    assert "password_too_long" in str(excinfo.value)


def test_hash_password_raises_on_multibyte_overflow():
    plain = "é" * 40
    assert len(plain.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES
    with pytest.raises(PasswordTooLongError):
        hash_password(plain)


def test_verify_password_returns_false_on_oversize_input():
    h = hash_password("SafePassword123!")
    assert verify_password("a" * 200, h) is False


def test_verify_password_returns_false_on_malformed_hash():
    assert verify_password("anything", "not-a-valid-bcrypt-hash") is False
    assert verify_password("anything", "") is False


@pytest.mark.asyncio
async def test_login_with_oversized_password_returns_401_not_500(client, admin_user):
    resp = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "a" * 200,
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_change_password_oversized_new_password_is_rejected(
    client, admin_user, db_session,
):
    """422 from schema validation, never reaches bcrypt, no DB mutation."""
    login = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert login.status_code == 200

    oversized = "Aa1!" + "x" * MAX_BCRYPT_PASSWORD_BYTES  # > 72 bytes
    resp = await client.post("/api/auth/change-password", json={
        "current_password": "TestPassword123!",
        "new_password": oversized,
        "confirm_password": oversized,
    })
    assert resp.status_code == 422

    # Hashed password must remain the original one (no DB mutation).
    refreshed = (
        await db_session.execute(select(User).where(User.username == "admin"))
    ).scalar_one()
    assert verify_password("TestPassword123!", refreshed.hashed_password) is True
