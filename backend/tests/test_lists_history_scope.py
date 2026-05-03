"""History on a public_readonly list must stay scoped to its owner +
named contributors. The list ITEMS are public; the audit log of *who*
added them is not.
"""
from __future__ import annotations

import pytest

from core.security import hash_password
from models.user import User
from models.portal.profile import UserProfile
from models.portal.social import UserList, UserListContributor


async def _portal_login(client, *, username: str, password: str) -> None:
    r = await client.post("/api/auth/portal-login", json={
        "username": username,
        "password": password,
    })
    assert r.status_code == 200, r.text


async def _make_user(db_session, *, username: str, password: str = "AnyPassword123!"):
    user = User(
        username=username,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role="admin" if username == "admin" else "viewer",
        account_active=True,
        can_lists=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


@pytest.mark.asyncio
async def test_owner_sees_history_on_public_readonly_list(client, admin_user, db_session):
    """The owner is always allowed to read the history of their list."""
    await _portal_login(client, username="admin", password="TestPassword123!")

    lst = UserList(
        user_id=admin_user.id,
        name="Coups de cœur",
        privacy="public_readonly",
        content_type="mixed",
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)

    r = await client.get(f"/api/portal/lists/{lst.id}/history")
    assert r.status_code == 200
    assert "items" in r.json()


@pytest.mark.asyncio
async def test_contributor_sees_history_on_public_readonly_list(client, admin_user, db_session):
    """A contributor named on the list must keep history access."""
    await _portal_login(client, username="admin", password="TestPassword123!")

    bob, _ = await _make_user(db_session, username="bob")
    lst = UserList(
        user_id=bob.id,
        name="Top 10",
        privacy="public_readonly",
        content_type="mixed",
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)

    db_session.add(UserListContributor(list_id=lst.id, user_id=admin_user.id))
    await db_session.commit()

    r = await client.get(f"/api/portal/lists/{lst.id}/history")
    assert r.status_code == 200
    assert "items" in r.json()


@pytest.mark.asyncio
async def test_random_viewer_does_not_see_history_on_public_readonly_list(client, admin_user, db_session):
    """A user who is neither owner nor contributor receives an empty
    history payload — no leak of who added/removed which item."""
    await _portal_login(client, username="admin", password="TestPassword123!")

    bob, _ = await _make_user(db_session, username="bob")
    lst = UserList(
        user_id=bob.id,
        name="Soirée potes",
        privacy="public_readonly",
        content_type="mixed",
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)

    r = await client.get(f"/api/portal/lists/{lst.id}/history")
    assert r.status_code == 200
    assert r.json() == {"items": []}
