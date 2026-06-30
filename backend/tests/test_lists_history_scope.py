"""History on a public_readonly list must stay scoped to its owner +
named contributors. The list ITEMS are public; the audit log of *who*
added them is not.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.user import User
from models.portal.profile import UserProfile
from models.portal.social import UserList, UserListContributor, UserListHistory
from services.portal._pseudo_words import generate_pseudo


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
async def test_owner_sees_history_on_public_readonly_list(client, admin_user, db_session, portal_login):
    """The owner is always allowed to read the history of their list."""
    await portal_login(client)

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
async def test_contributor_sees_history_on_public_readonly_list(client, admin_user, db_session, portal_login):
    """A contributor named on the list must keep history access."""
    await portal_login(client)

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
async def test_random_viewer_does_not_see_history_on_public_readonly_list(client, admin_user, db_session, portal_login):
    """A user who is neither owner nor contributor receives an empty
    history payload — no leak of who added/removed which item."""
    await portal_login(client)

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


@pytest.mark.asyncio
async def test_history_serves_pseudo_not_raw_emby_login(client, admin_user, db_session, portal_login):
    """The history surfaces each actor's portal pseudo, never the raw Emby
    ``User.username`` (pseudonymisation across collaborators)."""
    await portal_login(client)

    # A contributor with a distinct Emby login and a chosen portal pseudo.
    u1, _ = await _make_user(db_session, username="u1login")
    p1 = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == u1.id)
    )).scalar_one()
    p1.display_name = "Curator"
    p1.display_name_must_set = False
    db_session.add(p1)

    lst = UserList(
        user_id=admin_user.id, name="Shared",
        privacy="collaborative", content_type="mixed",
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)

    db_session.add(UserListContributor(list_id=lst.id, user_id=u1.id))
    db_session.add(UserListHistory(
        list_id=lst.id, user_id=u1.id, action="add",
        tmdb_id=1, media_type="movie", title="X",
    ))
    await db_session.commit()

    r = await client.get(f"/api/portal/lists/{lst.id}/history")
    assert r.status_code == 200
    names = [it["username"] for it in r.json()["items"]]
    assert "u1login" not in names
    assert "Curator" in names


async def _seed_silent_actor_history(db_session, admin_user, *, login="silentlogin"):
    """Owner-held list with one history row authored by a silent account
    (``display_name_must_set`` still True). Returns (list, actor)."""
    silent, _ = await _make_user(db_session, username=login)
    p = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == silent.id)
    )).scalar_one()
    # A leftover auto-seeded display_name is present, but the account is
    # still flagged "must set" — the resolver must ignore it and emit the
    # anonymous alias, never the stale name nor the raw Emby login.
    p.display_name = "StaleName"
    p.display_name_must_set = True
    db_session.add(p)

    lst = UserList(
        user_id=admin_user.id, name="Shared",
        privacy="collaborative", content_type="mixed",
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)

    db_session.add(UserListContributor(list_id=lst.id, user_id=silent.id))
    db_session.add(UserListHistory(
        list_id=lst.id, user_id=silent.id, action="add",
        tmdb_id=1, media_type="movie", title="X",
    ))
    await db_session.commit()
    return lst, silent


@pytest.mark.asyncio
async def test_history_anonymises_silent_account_to_fr_alias(client, admin_user, db_session, portal_login):
    """A silent account surfaces as the localized anonymous alias — never
    the raw Emby login, nor a stale auto-seeded display_name."""
    await portal_login(client)
    lst, silent = await _seed_silent_actor_history(db_session, admin_user)

    r = await client.get(f"/api/portal/lists/{lst.id}/history")
    assert r.status_code == 200
    names = [it["username"] for it in r.json()["items"]]
    assert "silentlogin" not in names
    assert "StaleName" not in names
    assert generate_pseudo(silent.id, "fr") in names


@pytest.mark.asyncio
async def test_history_anonymous_alias_localises_to_en(client, admin_user, db_session, portal_login):
    """Accept-Language: en localizes the anonymous pseudo to Blue-Fox-NN
    (the same silent account that renders Renard-Bleu-NN in French)."""
    await portal_login(client)
    lst, silent = await _seed_silent_actor_history(db_session, admin_user)

    r = await client.get(
        f"/api/portal/lists/{lst.id}/history",
        headers={"Accept-Language": "en"},
    )
    assert r.status_code == 200
    names = [it["username"] for it in r.json()["items"]]
    assert generate_pseudo(silent.id, "en") in names
    assert generate_pseudo(silent.id, "fr") not in names


@pytest.mark.asyncio
async def test_history_system_action_has_null_username(client, admin_user, db_session, portal_login):
    """A purged/system action (user_id NULL via SET NULL) surfaces a null
    username instead of fabricating an alias from a missing id."""
    await portal_login(client)

    lst = UserList(
        user_id=admin_user.id, name="Shared",
        privacy="collaborative", content_type="mixed",
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)

    db_session.add(UserListHistory(
        list_id=lst.id, user_id=None, action="remove",
        tmdb_id=2, media_type="movie", title="Y",
    ))
    await db_session.commit()

    r = await client.get(f"/api/portal/lists/{lst.id}/history")
    assert r.status_code == 200
    sys_rows = [it for it in r.json()["items"] if it["user_id"] is None]
    assert sys_rows
    assert all(it["username"] is None for it in sys_rows)
