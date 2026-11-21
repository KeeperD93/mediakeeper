"""Every cached digest goes when a member's podium row changes outside their own
profile save: an admin rename, a name reset, a forced-public profile, an avatar."""
from __future__ import annotations

import pytest

from services.portal import admin_users, admin_users_security
from services.portal import daily_digest as dd_svc
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token


@pytest.fixture
def cleared(monkeypatch) -> list[bool]:
    calls: list[bool] = []
    monkeypatch.setattr(dd_svc, "clear_cache", lambda: calls.append(True))
    return calls


@pytest.mark.asyncio
async def test_an_admin_rename_rebuilds_every_digest(db_session, cleared):
    user, profile = await make_portal_user(db_session, username="alice", display_name="Alice")
    await admin_users.update_user_identity(db_session, profile, user, first_name="Alice")
    assert cleared == []  # the name did not change

    await admin_users.update_user_identity(db_session, profile, user, display_name="Alicia")
    assert cleared == [True]


@pytest.mark.asyncio
async def test_a_name_reset_rebuilds_every_digest(db_session, admin_user, cleared):
    _, profile = await make_portal_user(db_session, username="alice", display_name="Alice")
    await admin_users_security.reset_display_name(db_session, profile, admin_user_id=admin_user.id)
    assert cleared == [True]


@pytest.mark.asyncio
async def test_a_forced_public_profile_rebuilds_every_digest(client, db_session, cleared):
    user, _ = await make_portal_user(db_session, username="alice", display_name="Alice", is_public=False)
    admin, _ = await make_portal_user(db_session, username="olivia", display_name="Olivia", role="admin")
    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))
    resp = await client.put(f"/api/portal/admin/users/{user.id}/force-public", params={"forced": True})
    assert resp.status_code == 200, resp.text
    assert cleared == [True]


@pytest.mark.asyncio
async def test_removing_an_avatar_rebuilds_every_digest(client, db_session, cleared):
    user, _ = await make_portal_user(db_session, username="alice", display_name="Alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    assert (await client.delete("/api/portal/profiles/me/avatar")).status_code == 200
    assert cleared == [True]
