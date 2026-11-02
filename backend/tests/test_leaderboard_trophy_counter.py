"""The monthly stats count the trophies unlocked this month, excluded accounts left out,
and each row of the ranking carries the trophies its player won this month."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from models.portal.achievement import Achievement, UserAchievement
from models.portal.xp_ledger import XpLedger
from services.portal._leaderboard_helpers import trophies_by_user_since
from services.portal.profile_stats_ranking import compute_ranking
from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)

MONTHLY_URL = "/api/portal/achievements/leaderboard/monthly"


def _month_start() -> datetime:
    return datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )


async def _add_trophy(
    db_session,
    user_id: int,
    achievement_id: str,
    *,
    unlocked_at: datetime | None,
) -> None:
    if await db_session.get(Achievement, achievement_id) is None:
        db_session.add(Achievement(
            id=achievement_id,
            category="test",
            name_key="portal.achievements.test",
            description_key="portal.achievements.test_desc",
            icon="Trophy",
            condition_type="test",
        ))
    db_session.add(UserAchievement(
        user_id=user_id,
        achievement_id=achievement_id,
        progress=1,
        unlocked=unlocked_at is not None,
        unlocked_at=unlocked_at,
        notified=False,
    ))
    await db_session.commit()


async def _get_stats(client, viewer) -> dict:
    client.cookies.set(PORTAL_COOKIE, portal_token(viewer.username))
    resp = await client.get(MONTHLY_URL)
    assert resp.status_code == 200
    return resp.json()["stats"]


@pytest.mark.asyncio
async def test_counts_only_trophies_unlocked_this_month(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    db_session.add(XpLedger(user_id=alice.id, action="watch_movie", reference="a", xp=10))
    now = datetime.now(timezone.utc)
    await _add_trophy(db_session, alice.id, "this_month_a", unlocked_at=now)
    await _add_trophy(db_session, alice.id, "this_month_b", unlocked_at=_month_start())
    await _add_trophy(
        db_session, alice.id, "last_month",
        unlocked_at=_month_start() - timedelta(seconds=1),
    )
    await _add_trophy(db_session, alice.id, "in_progress", unlocked_at=None)

    stats = await _get_stats(client, alice)

    assert stats["total_trophies_month"] == 2


@pytest.mark.asyncio
async def test_excluded_accounts_do_not_count(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    db_session.add(XpLedger(user_id=alice.id, action="watch_movie", reference="a", xp=10))
    gone, gone_profile = await make_portal_user(db_session, username="gone")
    gone_profile.account_active = False
    db_session.add(gone_profile)
    now = datetime.now(timezone.utc)
    await _add_trophy(db_session, alice.id, "kept", unlocked_at=now)
    await _add_trophy(db_session, gone.id, "left_out", unlocked_at=now)

    stats = await _get_stats(client, alice)

    assert stats["total_trophies_month"] == 1


@pytest.mark.asyncio
async def test_a_player_without_activity_still_adds_their_trophy(client, db_session):
    """They are not ranked, yet the trophy was handed out this month."""
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    db_session.add(XpLedger(user_id=alice.id, action="watch_movie", reference="a", xp=10))
    await _add_trophy(db_session, bob.id, "trophy", unlocked_at=datetime.now(timezone.utc))

    stats = await _get_stats(client, alice)

    assert stats["total_players"] == 1
    assert stats["total_trophies_month"] == 1


@pytest.mark.asyncio
async def test_empty_ranking_keeps_the_count(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    await _add_trophy(db_session, alice.id, "trophy", unlocked_at=datetime.now(timezone.utc))

    stats = await _get_stats(client, alice)

    assert stats["total_players"] == 0
    assert stats["total_trophies_month"] == 1


async def _three_players_with_trophies(db_session) -> tuple:
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    carol, _ = await make_portal_user(db_session, username="carol")
    for user, xp in ((alice, 30), (bob, 20), (carol, 10)):
        db_session.add(
            XpLedger(user_id=user.id, action="watch_movie", reference=user.username, xp=xp)
        )
    this_month = _month_start() + timedelta(seconds=1)
    await _add_trophy(db_session, alice.id, "first", unlocked_at=this_month)
    await _add_trophy(db_session, alice.id, "second", unlocked_at=_month_start())
    await _add_trophy(
        db_session, alice.id, "last_month",
        unlocked_at=_month_start() - timedelta(seconds=1),
    )
    await _add_trophy(db_session, alice.id, "in_progress", unlocked_at=None)
    await _add_trophy(db_session, bob.id, "first", unlocked_at=this_month)
    return alice, bob, carol


@pytest.mark.asyncio
async def test_each_row_carries_the_trophies_its_player_won_this_month(client, db_session):
    alice, bob, carol = await _three_players_with_trophies(db_session)

    client.cookies.set(PORTAL_COOKIE, portal_token(alice.username))
    resp = await client.get(MONTHLY_URL)

    assert resp.status_code == 200
    won = {row["user_id"]: row["trophies_won"] for row in resp.json()["items"]}
    assert won == {alice.id: 2, bob.id: 1, carol.id: 0}


@pytest.mark.asyncio
async def test_a_viewer_outside_the_list_keeps_their_trophies(client, db_session):
    alice, bob, _ = await _three_players_with_trophies(db_session)

    client.cookies.set(PORTAL_COOKIE, portal_token(bob.username))
    resp = await client.get(f"{MONTHLY_URL}?limit=1")

    assert resp.status_code == 200
    body = resp.json()
    assert [row["user_id"] for row in body["items"]] == [alice.id]
    assert body["viewer_entry"]["trophies_won"] == 1


@pytest.mark.asyncio
async def test_my_profile_rows_carry_the_trophies_too(db_session):
    alice, bob, carol = await _three_players_with_trophies(db_session)

    ranking = await compute_ranking(db_session, carol)

    won = {row["user_id"]: row["trophies_won"] for row in ranking["leaderboard"]}
    assert won == {alice.id: 2, bob.id: 1, carol.id: 0}


@pytest.mark.asyncio
async def test_no_player_means_no_trophy_query(db_session):
    assert await trophies_by_user_since(db_session, [], _month_start()) == {}
