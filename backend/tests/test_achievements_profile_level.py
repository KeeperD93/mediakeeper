"""Veteran reads the level stored now, not the one the session loaded before."""
import pytest
from sqlalchemy import select, update

from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from services.portal.achievements import check_all_achievements, seed_achievements
from tests._portal_profile_helpers import make_portal_user


async def _veteran_unlocked(db, user_id: int) -> bool:
    row = (await db.execute(select(UserAchievement.unlocked).where(
        UserAchievement.user_id == user_id, UserAchievement.achievement_id == "veteran_1",
    ))).scalar_one_or_none()
    return bool(row)


@pytest.mark.asyncio
async def test_veteran_reads_a_level_lowered_after_the_session_loaded_it(db_session):
    await seed_achievements(db_session)
    user, profile = await make_portal_user(db_session, username="alice")
    profile.level = 5
    await db_session.commit()
    # Lowered by another session (a correction, the background worker); this one keeps level 5.
    await db_session.execute(
        update(UserProfile).where(UserProfile.user_id == user.id).values(level=1)
        .execution_options(synchronize_session=False)
    )
    await db_session.commit()
    assert profile.level == 5

    await check_all_achievements(db_session, user.id)
    assert not await _veteran_unlocked(db_session, user.id)


@pytest.mark.asyncio
async def test_veteran_is_granted_on_the_level_stored(db_session):
    await seed_achievements(db_session)
    user, profile = await make_portal_user(db_session, username="bob")
    profile.level = 5
    await db_session.commit()

    await check_all_achievements(db_session, user.id)
    assert await _veteran_unlocked(db_session, user.id)
