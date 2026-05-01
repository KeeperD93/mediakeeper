"""Admin accounts must never appear in the leaderboard endpoints.

Covers ``/api/portal/achievements/leaderboard`` (XP-based) which is the
endpoint the public leaderboard view consumes.
"""
from __future__ import annotations

import pytest

from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)


@pytest.mark.asyncio
async def test_achievements_leaderboard_excludes_admin(client, db_session):
    admin, ap = await make_portal_user(
        db_session, username="admin", display_name="admin", role="admin",
    )
    ap.xp = 99999
    me, mp = await make_portal_user(db_session, username="alice")
    mp.xp = 100
    other, op = await make_portal_user(db_session, username="bob")
    op.xp = 50
    db_session.add_all([ap, mp, op])
    await db_session.commit()

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard?limit=20")
    assert resp.status_code == 200
    items = resp.json()["items"]
    user_ids = [it["user_id"] for it in items]
    assert admin.id not in user_ids
    assert me.id in user_ids
    assert other.id in user_ids
