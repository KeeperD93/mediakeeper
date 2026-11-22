"""Admin XP tools write to the ledger the XP they really changed, and take back
no more than a trophy gave."""
import pytest
from sqlalchemy import func, select

from models.portal.achievement import Achievement, UserAchievement
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.portal.admin_debug import (
    ADMIN_GRANT_ACTION,
    admin_grant_xp,
    admin_reset_achievement_for_all,
    admin_set_level,
)
from services.portal.xp import level_floor_xp
from tests._watch_xp_helpers import account

pytestmark = pytest.mark.asyncio


async def with_xp(db, name: str, xp: int) -> int:
    """An account holding ``xp``, all of it in the ledger; returns its user id."""
    user_id = await account(db, name)
    profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalar_one()
    profile.xp = xp
    if xp:
        db.add(XpLedger(user_id=user_id, action="request_created", reference="request:1", xp=xp))
    await db.commit()
    return user_id


async def xp_and_ledger(db, user_id: int) -> tuple[int, int]:
    xp = await db.scalar(select(UserProfile.xp).where(UserProfile.user_id == user_id))
    ledger = await db.scalar(select(func.coalesce(func.sum(XpLedger.xp), 0)).where(XpLedger.user_id == user_id))
    return xp, ledger


async def _admin_rows(db, user_id: int) -> list[int]:
    found = await db.execute(
        select(XpLedger.xp).where(XpLedger.user_id == user_id, XpLedger.action == ADMIN_GRANT_ACTION)
    )
    return list(found.scalars())


async def test_a_removal_below_0_records_only_what_was_taken(db_session):
    alice = await with_xp(db_session, "alice", 20)

    assert (await admin_grant_xp(db_session, alice, -100, note="test"))["xp"] == 0

    assert await _admin_rows(db_session, alice) == [-20]
    assert await xp_and_ledger(db_session, alice) == (0, 0)


async def test_a_removal_from_a_player_at_0_records_nothing(db_session):
    bob = await with_xp(db_session, "bob", 0)

    assert (await admin_grant_xp(db_session, bob, -50, note="test"))["xp"] == 0

    assert await _admin_rows(db_session, bob) == []


async def test_setting_the_level_a_player_already_starts_records_nothing(db_session):
    carol = await with_xp(db_session, "carol", level_floor_xp(3))

    result = await admin_set_level(db_session, carol, 3)

    assert (result["xp"], result["level"], result["delta"]) == (level_floor_xp(3), 3, 0)
    assert await _admin_rows(db_session, carol) == []


async def _trophy_given(db, user_id: int, *, unlocked: bool = True, row: bool = True) -> None:
    """``user_id`` got the test trophy and its 20 XP (``row=False``: the trophy alone was taken off since)."""
    if await db.get(Achievement, "test-trophy") is None:
        db.add(Achievement(
            id="test-trophy", category="watching", name_key="k", description_key="d", icon="Film",
            condition_type="watch_movies",
        ))
    if row:
        db.add(UserAchievement(user_id=user_id, achievement_id="test-trophy", unlocked=unlocked))
    if unlocked:
        profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalar_one()
        profile.xp += 20
        db.add(XpLedger(user_id=user_id, action="achievement_unlocked", reference="ach:test-trophy", xp=20))
    await db.commit()


async def test_a_reset_for_all_takes_back_the_trophy_xp_only(db_session):
    alice = await with_xp(db_session, "alice", 30)
    profile = (await db_session.execute(select(UserProfile).where(UserProfile.user_id == alice))).scalar_one()
    profile.xp += 100  # earned before the ledger existed
    await _trophy_given(db_session, alice)
    carol = await with_xp(db_session, "carol", 10)
    await _trophy_given(db_session, carol, unlocked=False)  # on her way to it

    result = await admin_reset_achievement_for_all(db_session, "test-trophy")

    assert await xp_and_ledger(db_session, alice) == (130, 30)
    assert await xp_and_ledger(db_session, carol) == (10, 10)
    assert (result["user_achievements_removed"], result["xp_ledger_removed"], result["profiles_rebuilt"]) == (2, 1, 1)


async def test_a_reset_for_all_takes_back_the_xp_of_a_trophy_no_longer_held(db_session):
    bob = await with_xp(db_session, "bob", 0)
    await _trophy_given(db_session, bob, row=False)  # unlocked meanwhile, or taken off alone

    await admin_reset_achievement_for_all(db_session, "test-trophy")

    assert await xp_and_ledger(db_session, bob) == (0, 0)
