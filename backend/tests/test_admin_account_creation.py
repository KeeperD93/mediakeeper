"""Users page, "Create an administrator": the local account it makes is for a
name declared in MK_ADMIN_USERS, can sign in, and must change its password
first. Synthetic users only."""
from __future__ import annotations

import pytest
from sqlalchemy import func, select

from constants.security import ACCOUNT_DISABLED
from core.security import create_access_token
from models.portal.audit import AdminAuditLog
from models.portal.profile import UserProfile
from models.user import User

NEW_ADMIN = "second-admin"
PASSWORD = "Test-Pass-12345"
URL = "/api/portal/admin/users/local"


@pytest.fixture(autouse=True)
def emby_users(monkeypatch):
    """The Emby users the creation compares names with: none unless a test adds some."""
    users: list[dict] = []

    async def _list(_db):
        return users

    monkeypatch.setattr("services.portal.admin_users_emby.list_emby_users", _list)
    return users


async def _create(client, admin_user, username: str, **fields) -> dict:
    client.cookies.set(
        "mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )
    resp = await client.post(URL, json={"username": username, "password": PASSWORD, **fields})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _accounts_named(db_session, username: str) -> int:
    return (await db_session.execute(
        select(func.count()).select_from(User).where(User.username == username)
    )).scalar_one()


async def _created(db_session, body: dict) -> tuple[User, UserProfile]:
    user = (await db_session.execute(select(User).where(User.id == body["user_id"]))).scalar_one()
    profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.id == body["profile_id"])
    )).scalar_one()
    return user, profile


@pytest.mark.asyncio
async def test_created_admin_signs_in_and_must_change_password(
    client, admin_user, db_session, monkeypatch,
):
    monkeypatch.setenv("MK_ADMIN_USERS", f"admin,{NEW_ADMIN}")
    body = await _create(client, admin_user, NEW_ADMIN)
    assert body["ok"] is True

    user, profile = await _created(db_session, body)
    assert user.is_active is True
    assert user.must_change_password is True
    assert (profile.role, profile.source, profile.emby_user_id) == ("admin", "local", None)
    audit = (await db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.target_user_id == user.id)
    )).scalar_one()
    assert audit.payload["role"] == "admin"

    resp = await client.post(
        "/api/auth/portal-login", json={"username": NEW_ADMIN, "password": PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["scope"] == "admin"
    assert resp.json()["must_change_password"] is True


@pytest.mark.asyncio
async def test_refuses_a_name_not_declared_admin(client, admin_user, db_session, monkeypatch):
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")
    assert await _create(client, admin_user, NEW_ADMIN) == {"error": "not_admin_name"}
    assert await _accounts_named(db_session, NEW_ADMIN) == 0


@pytest.mark.asyncio
async def test_name_must_be_spelled_as_declared(client, admin_user, db_session, monkeypatch):
    """Sign-in compares the account name with the list exactly: creation does too."""
    monkeypatch.setenv("MK_ADMIN_USERS", "admin,Second-Admin")
    assert await _create(client, admin_user, NEW_ADMIN) == {"error": "not_admin_name"}

    body = await _create(client, admin_user, "  Second-Admin  ")
    user, _ = await _created(db_session, body)
    assert user.username == "Second-Admin"


@pytest.mark.asyncio
async def test_refuses_an_accented_capital(client, admin_user, db_session, monkeypatch):
    """The database lower() leaves an accented capital as it is (SQLite here,
    PostgreSQL in the C locale): such an account could never sign in."""
    monkeypatch.setenv("MK_ADMIN_USERS", "admin,Élodie,élodie")
    assert await _create(client, admin_user, "Élodie") == {"error": "username_accented_capital"}
    assert await _accounts_named(db_session, "Élodie") == 0

    body = await _create(client, admin_user, "élodie")
    assert body["ok"] is True
    resp = await client.post("/api/auth/login", json={"username": "Élodie", "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    assert resp.json()["must_change_password"] is True


@pytest.mark.asyncio
async def test_refuses_an_emby_namesake(client, admin_user, db_session, monkeypatch, emby_users):
    """The Emby sign-in finds an account by name: an Emby user of the same name
    would enter the admin account with their Emby password."""
    monkeypatch.setenv("MK_ADMIN_USERS", f"admin,{NEW_ADMIN}")
    emby_users.append({"Name": "Second-Admin", "Id": "emby-1"})
    assert await _create(client, admin_user, NEW_ADMIN) == {"error": "username_on_emby"}
    assert await _accounts_named(db_session, NEW_ADMIN) == 0


@pytest.mark.asyncio
async def test_unticked_active_box_keeps_the_account_off(client, admin_user, db_session, monkeypatch):
    monkeypatch.setenv("MK_ADMIN_USERS", f"admin,{NEW_ADMIN}")
    body = await _create(client, admin_user, NEW_ADMIN, account_active=False)
    user, profile = await _created(db_session, body)
    assert user.is_active is False
    assert profile.account_active is False

    resp = await client.post("/api/auth/login", json={"username": NEW_ADMIN, "password": PASSWORD})
    assert resp.status_code == 403
    assert resp.json()["detail"] == ACCOUNT_DISABLED


@pytest.mark.asyncio
async def test_role_is_not_accepted(client, admin_user, db_session, monkeypatch):
    """The screen only creates administrators: a role sent along is refused."""
    monkeypatch.setenv("MK_ADMIN_USERS", f"admin,{NEW_ADMIN}")
    client.cookies.set(
        "mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )
    resp = await client.post(
        URL, json={"username": NEW_ADMIN, "password": PASSWORD, "role": "viewer"},
    )
    assert resp.status_code == 422
    assert await _accounts_named(db_session, NEW_ADMIN) == 0
