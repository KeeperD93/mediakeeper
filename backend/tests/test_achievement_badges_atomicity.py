"""Pinning and unpinning rewrite the stored badge list, not the copy the route has loaded."""
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement, UserAchievement
from models.portal.profile import UserProfile
from services.portal.achievements_badges import pin_badge, unpin_badge
from tests._portal_profile_helpers import make_portal_user

BADGE_A, BADGE_B = "test-badge-a", "test-badge-b"


async def _alice_with_badges(db: AsyncSession) -> int:
    user, _ = await make_portal_user(db, username="alice")
    for badge in (BADGE_A, BADGE_B):
        db.add(Achievement(
            id=badge, category="standard", name_key=f"{badge}.name",
            description_key=f"{badge}.desc", icon="trophy", tier=1,
            xp_reward=10, threshold=1, condition_type="manual",
        ))
        db.add(UserAchievement(
            user_id=user.id, achievement_id=badge, progress=1,
            unlocked=True, notified=True, unlocked_at=datetime.now(UTC),
        ))
    await db.commit()
    return user.id


async def _load_as_the_route_does(db: AsyncSession, user_id: int) -> UserProfile:
    """``get_current_profile`` loads the profile in the session the route then hands over.

    Keep the returned object alive, as the route's ``up`` does: the session only holds it weakly.
    """
    return (await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )).scalar_one()


async def _pin_from_another_session(db: AsyncSession, user_id: int, badge: str) -> None:
    async with AsyncSession(db.bind, expire_on_commit=False) as other:
        assert await pin_badge(other, user_id, badge) is True


async def _stored_badges(db: AsyncSession, user_id: int) -> list[str]:
    async with AsyncSession(db.bind, expire_on_commit=False) as reader:
        return await reader.scalar(
            select(UserProfile.selected_badges).where(UserProfile.user_id == user_id)
        )


@pytest.mark.asyncio
async def test_a_pin_keeps_the_badge_another_session_pinned_meanwhile(db_session):
    user_id = await _alice_with_badges(db_session)
    profile = await _load_as_the_route_does(db_session, user_id)
    await _pin_from_another_session(db_session, user_id, BADGE_A)

    assert await pin_badge(db_session, user_id, BADGE_B) is True

    assert await _stored_badges(db_session, user_id) == [BADGE_A, BADGE_B]
    assert profile.selected_badges == [BADGE_A, BADGE_B]


@pytest.mark.asyncio
async def test_an_unpin_keeps_the_badge_another_session_pinned_meanwhile(db_session):
    user_id = await _alice_with_badges(db_session)
    assert await pin_badge(db_session, user_id, BADGE_A) is True
    profile = await _load_as_the_route_does(db_session, user_id)
    await _pin_from_another_session(db_session, user_id, BADGE_B)

    assert await unpin_badge(db_session, user_id, BADGE_A) is True

    assert await _stored_badges(db_session, user_id) == [BADGE_B]
    assert profile.selected_badges == [BADGE_B]
