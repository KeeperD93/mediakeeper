"""An imported Emby account gets its trophies checked at once, a deactivated one never."""
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

import api.portal_admin_users_emby as route
from core.security import create_access_token
from models.portal.profile import UserProfile
from models.user import User

IMPORT = "/api/portal/admin/users/emby/import"
EMBY_USERS = [{"Id": "emby-alice", "Name": "alice"}, {"Id": "emby-bob", "Name": "bob"}]


@pytest.fixture
def checks(monkeypatch) -> list[tuple[int, str]]:
    done: list[tuple[int, str]] = []

    async def spy(user_id, source):
        done.append((user_id, source))
        return []

    monkeypatch.setattr(route, "safe_check_all_achievements_in_new_session", spy)
    return done


async def _import(client, admin_user, ids: list[str]):
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))
    with patch("services.portal.admin_users_emby.list_emby_users", new=AsyncMock(return_value=EMBY_USERS)):
        return await client.post(IMPORT, json={"emby_user_ids": ids})


async def _user_id(db, name: str) -> int:
    return (await db.execute(select(User.id).where(User.username == name))).scalar_one()


@pytest.mark.asyncio
async def test_each_imported_account_is_checked(client, admin_user, db_session, checks):
    resp = await _import(client, admin_user, ["emby-alice", "emby-bob"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == 2
    expected = [(await _user_id(db_session, name), "emby_import") for name in ("alice", "bob")]
    assert sorted(checks) == sorted(expected)


@pytest.mark.asyncio
async def test_a_deactivated_account_named_in_an_import_is_not_checked(client, admin_user, db_session, checks):
    bob = User(username="bob", hashed_password="x", is_active=False, must_change_password=False)
    db_session.add(bob)
    await db_session.flush()
    db_session.add(UserProfile(user_id=bob.id, display_name="Bob", account_active=False, emby_user_id="emby-bob"))
    await db_session.commit()

    resp = await _import(client, admin_user, ["emby-alice", "emby-bob"])
    assert resp.json()["created"] == 1
    assert checks == [(await _user_id(db_session, "alice"), "emby_import")]


@pytest.mark.asyncio
async def test_nothing_is_checked_when_nothing_was_imported(client, admin_user, checks):
    resp = await _import(client, admin_user, ["emby-unknown"])
    assert resp.json().get("error") == "not_found"
    assert checks == []
