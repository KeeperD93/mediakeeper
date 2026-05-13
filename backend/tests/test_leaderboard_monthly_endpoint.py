"""Coverage for the dedicated /portal/leaderboard page endpoint.

``GET /api/portal/achievements/leaderboard/monthly`` returns the
top-N players by monthly XP — the source of truth for the premium
podium + ranks 4-100 table on /portal/leaderboard. The endpoint
shares its trust boundary with the profile mini-leaderboard: any
authenticated portal user can view it, while admin / soft-deleted /
deactivated accounts stay excluded.
"""
from __future__ import annotations

import pytest

from models.portal.xp_ledger import XpLedger
from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)


async def _grant_month_xp(db_session, user_id: int, xp: int, ref: str) -> None:
    db_session.add(XpLedger(user_id=user_id, action="watch_movie", reference=ref, xp=xp))
    await db_session.commit()


@pytest.mark.asyncio
async def test_monthly_leaderboard_returns_items(client, db_session):
    me, _ = await make_portal_user(db_session, username="alice")
    other, _ = await make_portal_user(db_session, username="bob")
    await _grant_month_xp(db_session, me.id, 1500, "month-alice")
    await _grant_month_xp(db_session, other.id, 800, "month-bob")

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard/monthly")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    user_ids = [it["user_id"] for it in body["items"]]
    assert me.id in user_ids
    assert other.id in user_ids
    # Entries carry the leaderboard-card schema (rank + tier + month_xp).
    first = body["items"][0]
    for key in ("rank", "user_id", "display_name", "level", "tier", "title_key", "month_xp"):
        assert key in first


@pytest.mark.asyncio
async def test_monthly_leaderboard_respects_limit(client, db_session):
    """``limit`` caps how many entries come back."""
    me, _ = await make_portal_user(db_session, username="alice")
    await _grant_month_xp(db_session, me.id, 100, "month-alice")
    for i in range(4):
        other, _ = await make_portal_user(db_session, username=f"bob{i}")
        await _grant_month_xp(db_session, other.id, 200 + i, f"month-bob{i}")

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard/monthly?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 3


@pytest.mark.asyncio
async def test_monthly_leaderboard_rejects_overshoot_limit(client, db_session):
    me, _ = await make_portal_user(db_session, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))

    resp = await client.get("/api/portal/achievements/leaderboard/monthly?limit=500")
    # FastAPI's Query(le=100) gates the upper bound — 500 is rejected
    # before the service runs.
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_monthly_leaderboard_excludes_local_admin_and_deactivated(client, db_session):
    """Local-only admin accounts (no Emby link), soft-deleted accounts
    and deactivated accounts must never appear in the public ranking
    — same exclusion contract as the profile mini-leaderboard."""
    me, _ = await make_portal_user(db_session, username="alice")
    # Production-shaped admin: local account, no emby_user_id. The
    # ``source != "emby"`` clause of _excluded_from_leaderboard pulls
    # it out of the ranking.
    local_admin, _ = await make_portal_user(
        db_session,
        username="admin",
        display_name="admin",
        role="admin",
        emby_user_id=None,
    )
    dead, dead_profile = await make_portal_user(db_session, username="zombie")
    dead_profile.account_active = False
    db_session.add(dead_profile)
    await db_session.commit()

    await _grant_month_xp(db_session, me.id, 100, "month-alice")
    await _grant_month_xp(db_session, local_admin.id, 99999, "month-admin")
    await _grant_month_xp(db_session, dead.id, 5000, "month-zombie")

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard/monthly")
    assert resp.status_code == 200
    user_ids = [it["user_id"] for it in resp.json()["items"]]
    assert me.id in user_ids
    assert local_admin.id not in user_ids
    assert dead.id not in user_ids


@pytest.mark.asyncio
async def test_monthly_leaderboard_requires_portal_auth(client, db_session):
    """No cookie → 401, even though the data is "public" for users."""
    client.cookies.clear()
    resp = await client.get("/api/portal/achievements/leaderboard/monthly")
    assert resp.status_code == 401
