"""Every player starts at level 1: the level computed from XP never goes below it."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from models.user import User
from services.portal.xp import (
    MAX_LEVEL,
    MIN_LEVEL,
    grant_xp,
    level_floor_xp,
    level_from_xp,
)


@pytest.mark.parametrize(("xp", "level"), [(0, 1), (99, 1), (100, 1), (299, 1), (300, 2)])
def test_level_from_xp_starts_at_level_1(xp, level):
    assert level_from_xp(xp) == level


@pytest.mark.parametrize(("level", "floor"), [(1, 0), (2, 300), (MAX_LEVEL, 127_500)])
def test_level_floor_xp_starts_the_first_level_at_0(level, floor):
    assert level_floor_xp(level) == floor


def test_each_level_starts_exactly_at_its_floor():
    for level in range(MIN_LEVEL, MAX_LEVEL + 1):
        assert level_from_xp(level_floor_xp(level)) == level
    for level in range(MIN_LEVEL + 1, MAX_LEVEL + 1):
        assert level_from_xp(level_floor_xp(level) - 1) == level - 1


@pytest.mark.asyncio
async def test_a_first_xp_grant_keeps_level_1(db_session):
    user = User(username="alice", hashed_password="x", is_active=True, must_change_password=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    db_session.add(UserProfile(
        user_id=user.id, display_name="Alice", role="viewer", account_active=True,
        emby_user_id="emby-alice",
    ))
    await db_session.commit()

    result = await grant_xp(db_session, user.id, "achievement_unlocked", "ach:test", xp_override=20)

    assert result["level"] == 1
    assert result["leveled_up"] is False
    async with AsyncSession(db_session.bind) as reader:
        stored = await reader.scalar(select(UserProfile.level).where(UserProfile.user_id == user.id))
    assert stored == 1
