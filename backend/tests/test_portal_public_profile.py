"""Rich public profile endpoint coverage (achievement ratio + ranking)."""
from __future__ import annotations

import pytest

from models.portal.xp_ledger import XpLedger
from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)


async def _grant_month_xp(db_session, user_id: int, xp: int, ref: str):
    """Stamp an XpLedger row for the current month so the public-profile
    endpoint (which mirrors /portal/me's monthly ranking) can rank the
    user. Uses a unique reference per row to dodge the dedup index.
    """
    db_session.add(XpLedger(user_id=user_id, action="watch_movie", reference=ref, xp=xp))
    await db_session.commit()


@pytest.mark.asyncio
async def test_public_profile_includes_achievements_ratio(client, db_session):
    user, profile = await make_portal_user(
        db_session, username="alice", display_name="Alice",
    )
    profile.bio = "Cinéphile averti"
    profile.xp = 4200
    db_session.add(profile)
    await db_session.commit()
    await _grant_month_xp(db_session, user.id, 4200, "month-alice")

    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.get(f"/api/portal/profiles/by-user-id/{user.id}/public")
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Alice"
    assert body["bio"] == "Cinéphile averti"
    assert body["is_self"] is True
    assert "achievements" in body
    assert "unlocked" in body["achievements"]
    assert "total" in body["achievements"]
    assert "ranking" in body
    assert body["ranking"]["position"] >= 1


@pytest.mark.asyncio
async def test_public_profile_private_blocks_strangers(client, db_session):
    me, _ = await make_portal_user(db_session, username="alice")
    target, _ = await make_portal_user(
        db_session, username="bob", display_name="Bob", is_public=False,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))

    resp = await client.get(f"/api/portal/profiles/by-user-id/{target.id}/public")
    # Private profiles return 404 (same shape as missing/admin) so the
    # caller cannot distinguish the underlying reason.
    assert resp.status_code == 404
    assert resp.json()["detail"] == "profile_not_found"


@pytest.mark.asyncio
async def test_public_profile_admin_self_preview_allowed(client, db_session):
    """The admin can preview their own profile (with admin_preview=true)
    so the 'View my public profile' CTA in /portal/settings doesn't 404."""
    admin, _ = await make_portal_user(
        db_session, username="admin", display_name="admin", role="admin",
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))
    resp = await client.get(f"/api/portal/profiles/by-user-id/{admin.id}/public")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_self"] is True
    assert body["admin_preview"] is True


@pytest.mark.asyncio
async def test_public_profile_admin_invisible_to_others(client, db_session):
    admin, _ = await make_portal_user(
        db_session, username="admin", display_name="admin", role="admin",
    )
    me, _ = await make_portal_user(db_session, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get(f"/api/portal/profiles/by-user-id/{admin.id}/public")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_profile_self_visible_when_private(client, db_session):
    me, _ = await make_portal_user(
        db_session, username="alice", is_public=False,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))

    resp = await client.get(f"/api/portal/profiles/by-user-id/{me.id}/public")
    assert resp.status_code == 200
    assert resp.json()["is_self"] is True


@pytest.mark.asyncio
async def test_public_profile_ranking_reflects_xp_order(client, db_session):
    """Mirrors /portal/me — ranking is the monthly XP ladder, not the
    all-time profile.xp column."""
    leader, _ = await make_portal_user(db_session, username="leader")
    me, _ = await make_portal_user(db_session, username="alice")
    await _grant_month_xp(db_session, leader.id, 9000, "month-leader")
    await _grant_month_xp(db_session, me.id, 1000, "month-alice")

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get(f"/api/portal/profiles/by-user-id/{me.id}/public")
    body = resp.json()
    assert body["ranking"]["position"] == 2
    assert body["ranking"]["total_public"] == 2
