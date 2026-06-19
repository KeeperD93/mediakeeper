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
async def test_public_profile_private_returns_placeholder(client, db_session):
    """Private profile fetched by a stranger now returns 200 with a
    minimal placeholder (``is_private=True`` + name + avatar). The
    leaderboard already exposes the user_id so masking as 404 here
    would only break the SPA's UX without gaining privacy."""
    me, _ = await make_portal_user(db_session, username="alice")
    target, _ = await make_portal_user(
        db_session, username="bob", display_name="Bob", is_public=False,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))

    resp = await client.get(f"/api/portal/profiles/by-user-id/{target.id}/public")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_private"] is True
    assert body["user_id"] == target.id
    assert body["display_name"] == "Bob"
    # Sensitive bits never leak in the placeholder shape.
    assert "bio" not in body
    assert "level" not in body
    assert "ranking" not in body
    assert "achievements" not in body


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
    body = resp.json()
    assert body["is_self"] is True
    # The owner still receives the full payload, NOT the private placeholder.
    assert body.get("is_private") is not True


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


@pytest.mark.asyncio
async def test_public_profile_hides_stale_cosmetics_without_writing(client, db_session):
    """Viewing a third party's public profile hides cosmetics they can no longer
    select (no unlocked achievement grants them), but never writes to their row:
    a read must not mutate the viewed user's profile."""
    from sqlalchemy import select
    from models.portal.profile import UserProfile

    _owner, profile = await make_portal_user(db_session, username="owner", display_name="Owner")
    profile.selected_title = "phantom_title"  # equipped but never unlocked
    db_session.add(profile)
    await db_session.commit()
    pid = profile.id

    viewer, _ = await make_portal_user(db_session, username="viewer")
    client.cookies.set(PORTAL_COOKIE, portal_token(viewer.username))

    resp = await client.get(f"/api/portal/profiles/{pid}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["selected_title"] is None  # hidden for display

    db_session.expire_all()
    stored = (await db_session.execute(
        select(UserProfile).where(UserProfile.id == pid)
    )).scalar_one()
    assert stored.selected_title == "phantom_title"  # row untouched (no write-on-read)


@pytest.mark.asyncio
async def test_own_profile_prunes_stale_cosmetics(client, db_session):
    """Loading your OWN profile (/me) clears cosmetics you can no longer select
    and persists the cleanup (own row, no cross-user race)."""
    from sqlalchemy import select
    from models.portal.profile import UserProfile

    me, profile = await make_portal_user(db_session, username="owner2", display_name="Owner2")
    profile.selected_title = "phantom_title"
    db_session.add(profile)
    await db_session.commit()
    uid = me.id

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/profiles/me")
    assert resp.status_code == 200, resp.text

    db_session.expire_all()
    stored = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == uid)
    )).scalar_one()
    assert stored.selected_title is None  # persisted cleanup
