"""A private profile leaves the ranking and its totals, but not the trophy counter."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from constants.leaderboard import LeaderboardPeriod
from models.portal.achievement import Achievement, UserAchievement
from models.portal.xp_ledger import XpLedger
from services.portal.monthly_ranking import MonthlyEntry, finished_month_rankings
from services.portal.profile_stats_ranking import (
    compute_leaderboard_only,
    compute_ranking,
)
from tests._portal_profile_helpers import make_portal_user

EVERY_PERIOD = list(LeaderboardPeriod)


def _last_month() -> datetime:
    """A moment well inside the previous month, whatever today's date."""
    first = datetime.now(UTC).replace(day=1, hour=12, minute=0, second=0, microsecond=0)
    return (first - timedelta(days=1)).replace(day=5)


def _xp(user, amount: int, created_at: datetime | None = None) -> XpLedger:
    return XpLedger(
        user_id=user.id,
        action="watch_movie",
        reference=f"{user.username}-{amount}",
        xp=amount,
        created_at=created_at or datetime.now(UTC),
    )


async def _alice_and_private_bob(db_session, *, created_at: datetime | None = None):
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, bob_profile = await make_portal_user(db_session, username="bob", is_public=False)
    db_session.add_all([_xp(alice, 30, created_at), _xp(bob, 200, created_at)])
    await db_session.commit()
    return alice, bob, bob_profile


async def _give_trophy(db_session, *users) -> None:
    db_session.add(Achievement(
        id="test_trophy",
        category="test",
        name_key="portal.achievements.test",
        description_key="portal.achievements.test_desc",
        icon="Trophy",
        condition_type="test",
    ))
    db_session.add_all([
        UserAchievement(
            user_id=user.id,
            achievement_id="test_trophy",
            progress=1,
            unlocked=True,
            unlocked_at=datetime.now(UTC),
            notified=False,
        )
        for user in users
    ])
    await db_session.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize("period", EVERY_PERIOD)
async def test_a_private_player_leaves_the_ranking_and_its_totals(db_session, period):
    alice, _, _ = await _alice_and_private_bob(db_session)

    body = await compute_leaderboard_only(db_session, period=period, viewer_user_id=alice.id)

    assert [row["user_id"] for row in body["items"]] == [alice.id]
    assert body["stats"]["total_players"] == 1
    assert body["stats"]["total_xp"] == 30


@pytest.mark.asyncio
@pytest.mark.parametrize("period", EVERY_PERIOD)
async def test_the_trophy_counter_keeps_private_players_only(db_session, period):
    alice, bob, _ = await _alice_and_private_bob(db_session)
    gone, gone_profile = await make_portal_user(db_session, username="gone")
    gone_profile.account_active = False
    db_session.add(gone_profile)
    await _give_trophy(db_session, alice, bob, gone)

    body = await compute_leaderboard_only(db_session, period=period)

    assert body["stats"]["total_trophies"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("period", EVERY_PERIOD)
async def test_a_ranking_left_empty_still_counts_the_private_trophy(db_session, period):
    bob, _ = await make_portal_user(db_session, username="bob", is_public=False)
    db_session.add(_xp(bob, 200))
    await _give_trophy(db_session, bob)

    body = await compute_leaderboard_only(db_session, period=period)

    assert body["items"] == []
    assert body["stats"]["total_players"] == 0
    assert body["stats"]["total_trophies"] == 1


@pytest.mark.asyncio
async def test_a_private_viewer_has_no_place_of_their_own(db_session):
    _, bob, _ = await _alice_and_private_bob(db_session)

    body = await compute_leaderboard_only(db_session, viewer_user_id=bob.id)

    assert body["viewer_rank"] is None
    assert body["viewer_entry"] is None
    assert not any(row["is_current_user"] for row in body["items"])


@pytest.mark.asyncio
async def test_my_profile_ranks_without_the_private_player(db_session):
    alice, bob, _ = await _alice_and_private_bob(db_session)

    theirs = await compute_ranking(db_session, alice, zone=UTC)
    own = await compute_ranking(db_session, bob, zone=UTC)

    assert (theirs["position"], theirs["total"]) == (1, 1)
    assert [row["user_id"] for row in theirs["leaderboard"]] == [alice.id]
    assert (own["position"], own["total"], own["percentile"], own["movement"]) == (0, 1, 0, 0)
    assert [row["user_id"] for row in own["leaderboard"]] == [alice.id]


@pytest.mark.asyncio
async def test_going_public_again_brings_the_player_back(db_session):
    alice, bob, bob_profile = await _alice_and_private_bob(db_session)
    bob_profile.is_public = True
    db_session.add(bob_profile)
    await db_session.commit()

    body = await compute_leaderboard_only(db_session)

    assert [row["user_id"] for row in body["items"]] == [bob.id, alice.id]


@pytest.mark.asyncio
async def test_a_private_player_takes_no_place_in_a_finished_month(db_session):
    moment = _last_month()
    alice, _, _ = await _alice_and_private_bob(db_session, created_at=moment)

    rankings = await finished_month_rankings(db_session)

    assert rankings[(moment.year, moment.month)] == [MonthlyEntry(alice.id, 30, 1)]
