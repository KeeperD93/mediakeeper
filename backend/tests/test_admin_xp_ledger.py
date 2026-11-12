"""Admin XP tools write to the ledger the XP they really changed."""
import pytest
from sqlalchemy import func, select

from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.portal.admin_debug import (
    ADMIN_GRANT_ACTION,
    admin_grant_xp,
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
