"""Finished months, and so the Competitor trophy, are cut at midnight in the saved zone."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from models.portal.achievement import UserAchievement
from models.portal.xp_ledger import XpLedger
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.portal import monthly_ranking
from services.portal.achievements import check_all_achievements, seed_achievements
from services.portal.monthly_ranking import MonthlyEntry, finished_month_rankings
from services.settings import set_setting
from tests._portal_profile_helpers import make_portal_user

# November begins here in Paris; in UTC, October lasts one more hour.
NOVEMBER_IN_PARIS = datetime(2026, 10, 31, 23, tzinfo=UTC)
LATE_OCTOBER_PLAY = NOVEMBER_IN_PARIS + timedelta(minutes=30)
MID_OCTOBER = datetime(2026, 10, 15, 12, tzinfo=UTC)
MID_DECEMBER = datetime(2026, 12, 15, 12, tzinfo=UTC)
COMPETITOR_FIRST = {f"competitor_{tier}" for tier in range(1, 5)}
COMPETITOR_TOP_3 = {f"competitor_{tier}" for tier in range(1, 4)}


def _freeze(monkeypatch, moment: datetime) -> None:
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment

    monkeypatch.setattr(monthly_ranking, "datetime", _Frozen)


def _row(user, xp: int, created_at: datetime) -> XpLedger:
    return XpLedger(
        user_id=user.id, action="watch_movie", reference=f"{xp}-{created_at}", xp=xp,
        created_at=created_at,
    )


async def _two_players(db) -> tuple:
    """On UTC months Bob wins October; on Paris months his last play falls in November."""
    await seed_achievements(db)
    alice, _ = await make_portal_user(db, username="alice")
    bob, _ = await make_portal_user(db, username="bob")
    db.add_all([
        _row(alice, 100, MID_OCTOBER),
        _row(bob, 60, MID_OCTOBER),
        _row(bob, 61, LATE_OCTOBER_PLAY),
    ])
    await db.commit()
    return alice, bob


async def _competitor_tiers(db, user) -> set[str]:
    await check_all_achievements(db, user.id, user.username)
    rows = (await db.execute(
        select(UserAchievement.achievement_id).where(
            UserAchievement.user_id == user.id,
            UserAchievement.unlocked.is_(True),
            UserAchievement.achievement_id.like("competitor_%"),
        )
    )).scalars().all()
    return set(rows)


@pytest.mark.asyncio
async def test_a_past_month_is_cut_in_the_saved_zone(db_session, monkeypatch):
    alice, bob = await _two_players(db_session)
    _freeze(monkeypatch, MID_DECEMBER)

    without_zone = await finished_month_rankings(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    in_paris = await finished_month_rankings(db_session)

    assert without_zone == {
        (2026, 10): [MonthlyEntry(bob.id, 121, 1), MonthlyEntry(alice.id, 100, 2)],
    }
    assert in_paris == {
        (2026, 10): [MonthlyEntry(alice.id, 100, 1), MonthlyEntry(bob.id, 60, 2)],
        (2026, 11): [MonthlyEntry(bob.id, 61, 1)],
    }


@pytest.mark.asyncio
async def test_the_month_ends_at_midnight_in_the_saved_zone(db_session, monkeypatch):
    """45 minutes into November in Paris: October is over there, not in UTC."""
    alice, bob = await _two_players(db_session)
    _freeze(monkeypatch, NOVEMBER_IN_PARIS + timedelta(minutes=45))

    assert await finished_month_rankings(db_session) == {}

    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    assert await finished_month_rankings(db_session) == {
        # Bob's play of the first hour of November belongs to the month in progress.
        (2026, 10): [MonthlyEntry(alice.id, 100, 1), MonthlyEntry(bob.id, 60, 2)],
    }


@pytest.mark.asyncio
async def test_the_month_goes_on_west_of_utc(db_session, monkeypatch):
    """Two hours into November in UTC, it is still October in New York."""
    await _two_players(db_session)
    _freeze(monkeypatch, datetime(2026, 11, 1, 2, tzinfo=UTC))

    assert (2026, 10) in await finished_month_rankings(db_session)

    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "America/New_York")
    assert await finished_month_rankings(db_session) == {}


@pytest.mark.asyncio
async def test_the_first_second_of_a_month_counts_for_it_and_not_the_one_before(
    db_session, monkeypatch,
):
    alice, _ = await make_portal_user(db_session, username="alice")
    db_session.add_all([
        _row(alice, 1, NOVEMBER_IN_PARIS - timedelta(seconds=1)),
        _row(alice, 2, NOVEMBER_IN_PARIS),
    ])
    await db_session.commit()
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    _freeze(monkeypatch, MID_DECEMBER)

    assert await finished_month_rankings(db_session) == {
        (2026, 10): [MonthlyEntry(alice.id, 1, 1)],
        (2026, 11): [MonthlyEntry(alice.id, 2, 1)],
    }


@pytest.mark.asyncio
async def test_competitor_goes_to_the_winner_of_the_month_without_a_zone(db_session, monkeypatch):
    alice, bob = await _two_players(db_session)
    _freeze(monkeypatch, MID_DECEMBER)

    assert await _competitor_tiers(db_session, bob) == COMPETITOR_FIRST
    assert await _competitor_tiers(db_session, alice) == COMPETITOR_TOP_3


@pytest.mark.asyncio
async def test_competitor_goes_to_the_winner_of_the_month_in_the_saved_zone(db_session, monkeypatch):
    alice, bob = await _two_players(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    _freeze(monkeypatch, MID_DECEMBER)

    assert await _competitor_tiers(db_session, alice) == COMPETITOR_FIRST
    # Bob's November was played alone, so it gives nothing on top of his 2nd place.
    assert await _competitor_tiers(db_session, bob) == COMPETITOR_TOP_3


@pytest.mark.asyncio
async def test_a_zone_that_cannot_load_keeps_the_utc_months(db_session, monkeypatch):
    alice, bob = await _two_players(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Mars/Olympus")
    _freeze(monkeypatch, MID_DECEMBER)

    assert await finished_month_rankings(db_session) == {
        (2026, 10): [MonthlyEntry(bob.id, 121, 1), MonthlyEntry(alice.id, 100, 2)],
    }
