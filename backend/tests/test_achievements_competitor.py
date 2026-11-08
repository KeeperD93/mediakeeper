"""Competitor follows the displayed ranking: finished months, 2 players minimum."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from models.portal.achievement import UserAchievement
from models.portal.xp_ledger import XpLedger
from services.portal import achievements_checks_progression
from services.portal._leaderboard_helpers import (
    activity_xp_by_user,
    excluded_from_leaderboard,
)
from services.portal.achievements import check_all_achievements, seed_achievements
from services.portal.monthly_ranking import MonthlyEntry, finished_month_rankings
from tests._portal_profile_helpers import make_portal_user

ALL_TIERS = {f"competitor_{tier}" for tier in range(1, 7)}
FIRST_TIERS = {"competitor_1", "competitor_2", "competitor_3", "competitor_4"}


def _month_start(months_ago: int = 0) -> datetime:
    start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    for _ in range(months_ago):
        start = (start - timedelta(days=1)).replace(day=1)
    return start


def _key(moment: datetime) -> tuple[int, int]:
    return moment.year, moment.month


def _row(user, xp: int, created_at: datetime, action: str = "watch_movie") -> XpLedger:
    return XpLedger(
        user_id=user.id,
        action=action,
        reference=f"{action}-{created_at.isoformat()}",
        xp=xp,
        created_at=created_at,
    )


def _last_month() -> datetime:
    """A moment well inside the previous month, whatever today's date."""
    return _month_start(1) + timedelta(days=5)


async def _add(db_session, *rows: XpLedger) -> None:
    db_session.add_all(rows)
    await db_session.commit()


async def _players(db_session, *names: str) -> list:
    await seed_achievements(db_session)
    return [(await make_portal_user(db_session, username=name))[0] for name in names]


async def _tiers(db_session, user) -> set[str]:
    """Run the real check, then return the Competitor tiers the player holds."""
    await check_all_achievements(db_session, user.id)
    rows = (await db_session.execute(
        select(UserAchievement.achievement_id).where(
            UserAchievement.user_id == user.id,
            UserAchievement.unlocked.is_(True),
            UserAchievement.achievement_id.in_(ALL_TIERS),
        )
    )).scalars().all()
    return set(rows)


@pytest.mark.asyncio
async def test_the_month_in_progress_unlocks_nothing(db_session):
    alice, bob = await _players(db_session, "alice", "bob")
    now = datetime.now(timezone.utc)
    await _add(db_session, _row(alice, 100, now), _row(bob, 50, now))

    assert await _tiers(db_session, alice) == set()


@pytest.mark.asyncio
async def test_a_finished_month_unlocks_the_tiers_of_each_position(db_session):
    names = [f"player{index:02d}" for index in range(1, 12)]
    players = await _players(db_session, *names)
    await _add(db_session, *(
        _row(player, 1000 - index * 10, _last_month())
        for index, player in enumerate(players)
    ))

    expected_by_position = {
        1: FIRST_TIERS,
        2: {"competitor_1", "competitor_2", "competitor_3"},
        3: {"competitor_1", "competitor_2", "competitor_3"},
        4: {"competitor_1", "competitor_2"},
        5: {"competitor_1", "competitor_2"},
        6: {"competitor_1"},
        10: {"competitor_1"},
        11: set(),
    }
    for position, expected in expected_by_position.items():
        assert await _tiers(db_session, players[position - 1]) == expected, position


@pytest.mark.asyncio
async def test_a_month_played_alone_counts_for_nothing_but_stays_ranked(db_session):
    alice, bob = await _players(db_session, "alice", "bob")
    await _add(
        db_session,
        _row(alice, 100, _last_month()),
        # A 0 XP row is not activity, so Bob does not make it a competition.
        _row(bob, 0, _last_month(), action="surprise_used"),
    )

    assert await _tiers(db_session, alice) == set()
    rankings = await finished_month_rankings(db_session)
    assert rankings[_key(_last_month())] == [MonthlyEntry(alice.id, 100, 1)]


@pytest.mark.asyncio
async def test_trophy_and_admin_xp_do_not_change_the_position(db_session):
    alice, bob = await _players(db_session, "alice", "bob")
    moment = _last_month()
    await _add(
        db_session,
        _row(alice, 100, moment),
        _row(bob, 50, moment),
        _row(bob, 1000, moment, action="achievement_unlocked"),
        _row(bob, 1000, moment, action="admin_grant"),
    )

    assert await _tiers(db_session, alice) == FIRST_TIERS
    assert "competitor_4" not in await _tiers(db_session, bob)


@pytest.mark.asyncio
async def test_players_tied_first_both_win_and_the_next_one_is_third(db_session):
    alice, bob, carol = await _players(db_session, "alice", "bob", "carol")
    moment = _last_month()
    await _add(
        db_session, _row(bob, 100, moment), _row(alice, 100, moment), _row(carol, 50, moment)
    )

    rankings = await finished_month_rankings(db_session)

    assert rankings[_key(moment)] == [
        MonthlyEntry(alice.id, 100, 1),
        MonthlyEntry(bob.id, 100, 1),
        MonthlyEntry(carol.id, 50, 3),
    ]
    assert await _tiers(db_session, alice) == FIRST_TIERS
    assert await _tiers(db_session, bob) == FIRST_TIERS
    assert "competitor_4" not in await _tiers(db_session, carol)


@pytest.mark.asyncio
async def test_an_excluded_account_takes_no_place_and_no_seat(db_session):
    await seed_achievements(db_session)
    alice, _ = await make_portal_user(db_session, username="alice")
    gone, gone_profile = await make_portal_user(db_session, username="gone")
    gone_profile.account_active = False
    db_session.add(gone_profile)
    await _add(db_session, _row(alice, 100, _last_month()), _row(gone, 1000, _last_month()))

    # Alice is alone once the excluded account is gone: no competition.
    assert await _tiers(db_session, alice) == set()

    bob, _ = await make_portal_user(db_session, username="bob")
    await _add(db_session, _row(bob, 50, _last_month()))

    assert await _tiers(db_session, alice) == FIRST_TIERS


@pytest.mark.asyncio
async def test_months_change_at_midnight_utc(db_session):
    alice, bob = await _players(db_session, "alice", "bob")
    two_months_ago = _month_start(1) - timedelta(seconds=1)
    await _add(
        db_session,
        _row(alice, 100, two_months_ago),
        _row(bob, 10, two_months_ago),
        _row(bob, 60, _month_start(1)),
        _row(alice, 15, _month_start() - timedelta(seconds=1)),
        _row(alice, 1000, _month_start()),
    )

    rankings = await finished_month_rankings(db_session)

    assert rankings == {
        _key(two_months_ago): [MonthlyEntry(alice.id, 100, 1), MonthlyEntry(bob.id, 10, 2)],
        _key(_month_start(1)): [MonthlyEntry(bob.id, 60, 1), MonthlyEntry(alice.id, 15, 2)],
    }


@pytest.mark.asyncio
async def test_a_finished_month_counts_every_activity_like_the_displayed_ranking(db_session):
    alice, bob, carol = await _players(db_session, "alice", "bob", "carol")
    moment = _last_month()
    await _add(
        db_session,
        # Distinct powers of two: a missing action cannot go unnoticed.
        _row(alice, 1, moment),
        _row(alice, 2, moment, action="watch_episode"),
        _row(alice, 4, moment, action="daily_login"),
        _row(alice, 8, moment, action="request_created"),
        _row(alice, 500, moment, action="achievement_unlocked"),
        _row(bob, 14, moment),
        _row(carol, 90, moment, action="request_created"),
    )

    excluded = await excluded_from_leaderboard(db_session)
    displayed = await activity_xp_by_user(db_session, excluded, _month_start(1), _month_start())
    rankings = await finished_month_rankings(db_session)

    expected = [(carol.id, 90), (alice.id, 15), (bob.id, 14)]
    assert [(e.user_id, e.xp) for e in rankings[_key(moment)]] == expected
    assert [(row.user_id, row.total_xp) for row in displayed] == expected


@pytest.mark.asyncio
async def test_three_months_first_unlock_the_next_tier_only(db_session):
    alice, bob = await _players(db_session, "alice", "bob")
    await _add(db_session, *(
        row
        for months_ago in (1, 2, 3)
        for row in (
            _row(alice, 100, _month_start(months_ago) + timedelta(days=5)),
            _row(bob, 50, _month_start(months_ago) + timedelta(days=5)),
        )
    ))

    assert await _tiers(db_session, alice) == FIRST_TIERS | {"competitor_5"}
    last_tier = (await db_session.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == alice.id,
            UserAchievement.achievement_id == "competitor_6",
        )
    )).scalar_one()
    assert last_tier.progress == 3


@pytest.mark.asyncio
async def test_a_held_tier_is_kept_and_a_locked_one_follows_the_ranking(db_session):
    alice, = await _players(db_session, "alice")
    db_session.add_all([
        UserAchievement(
            user_id=alice.id, achievement_id="competitor_1", progress=1,
            unlocked=True, unlocked_at=_last_month(), notified=False,
        ),
        UserAchievement(
            user_id=alice.id, achievement_id="competitor_5", progress=2,
            unlocked=False, notified=False,
        ),
    ])
    await db_session.commit()

    assert await _tiers(db_session, alice) == {"competitor_1"}
    locked = (await db_session.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == alice.id,
            UserAchievement.achievement_id == "competitor_5",
        )
    )).scalar_one()
    assert locked.progress == 0


@pytest.mark.asyncio
async def test_the_ranking_is_built_once_and_only_when_a_tier_is_left(db_session, monkeypatch):
    calls = 0

    async def spy(db):
        nonlocal calls
        calls += 1
        return await finished_month_rankings(db)

    monkeypatch.setattr(achievements_checks_progression, "finished_month_rankings", spy)
    alice, = await _players(db_session, "alice")

    await check_all_achievements(db_session, alice.id)
    assert calls == 1

    rows = (await db_session.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == alice.id,
            UserAchievement.achievement_id.in_(ALL_TIERS),
        )
    )).scalars().all()
    assert {row.achievement_id for row in rows} == ALL_TIERS
    for row in rows:
        row.unlocked = True
        row.unlocked_at = _last_month()
    await db_session.commit()

    await check_all_achievements(db_session, alice.id)
    assert calls == 1
