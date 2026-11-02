"""The daily digest and the admin dashboard show each player's XP of the month."""
from datetime import UTC, datetime, timedelta

import pytest

from models.portal.xp_ledger import XpLedger
from services.portal.daily_digest_sources import ranking_snapshot
from tests._portal_profile_helpers import make_portal_user


async def _two_players(db_session) -> tuple:
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    last_month = datetime.now(UTC).replace(day=1) - timedelta(days=1)
    db_session.add_all([
        XpLedger(user_id=alice.id, action="watch_movie", reference="a", xp=30),
        XpLedger(user_id=bob.id, action="watch_movie", reference="b", xp=20),
        XpLedger(
            user_id=bob.id, action="watch_episode", reference="old", xp=1000,
            created_at=last_month,
        ),
    ])
    await db_session.commit()
    return alice, bob


@pytest.mark.asyncio
async def test_the_digest_shows_the_xp_of_the_month(db_session):
    alice, bob = await _two_players(db_session)

    snapshot = await ranking_snapshot(db_session, alice)

    assert [(row["user_id"], row["period_xp"]) for row in snapshot["top3"]] == [
        (alice.id, 30),
        (bob.id, 20),
    ]


@pytest.mark.asyncio
async def test_the_admin_dashboard_shows_the_xp_of_the_month(authed_client, db_session):
    alice, bob = await _two_players(db_session)

    resp = await authed_client.get("/api/stats/portal-monthly-leaderboard")

    assert resp.status_code == 200
    assert [(row["user_id"], row["period_xp"]) for row in resp.json()["leaderboard"]] == [
        (alice.id, 30),
        (bob.id, 20),
    ]
