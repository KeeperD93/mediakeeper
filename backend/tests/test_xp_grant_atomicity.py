"""``grant_xp`` adds to the stored XP, not to the copy its caller has loaded."""
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from models.user import User
from services.portal.xp import grant_xp


async def _make_profile(db: AsyncSession) -> UserProfile:
    user = User(username="alice", hashed_password="x", is_active=True, must_change_password=False)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    profile = UserProfile(
        user_id=user.id, display_name="Alice", role="viewer", account_active=True, emby_user_id="emby-alice",
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@pytest.mark.asyncio
async def test_grant_keeps_the_xp_another_session_granted_meanwhile(db_session):
    profile = await _make_profile(db_session)
    async with AsyncSession(db_session.bind, expire_on_commit=False) as worker:
        await grant_xp(worker, profile.user_id, "watch_movie", "test-movie:2026-01-15")

    await grant_xp(db_session, profile.user_id, "achievement_unlocked", "ach:test", xp_override=20)

    async with AsyncSession(db_session.bind, expire_on_commit=False) as reader:
        stored = await reader.scalar(
            select(UserProfile.xp).where(UserProfile.user_id == profile.user_id)
        )
        ledger = await reader.scalar(
            select(func.sum(XpLedger.xp)).where(XpLedger.user_id == profile.user_id)
        )
    assert stored == ledger == 30
    assert profile.xp == 30


@pytest.mark.asyncio
async def test_grant_keeps_the_unsaved_changes_of_the_loaded_profile(db_session):
    profile = await _make_profile(db_session)
    profile.bio = "Test bio"

    await grant_xp(db_session, profile.user_id, "watch_movie", "test-movie:2026-01-15")

    async with AsyncSession(db_session.bind, expire_on_commit=False) as reader:
        stored = await reader.scalar(
            select(UserProfile.bio).where(UserProfile.user_id == profile.user_id)
        )
    assert stored == "Test bio"
    assert profile.xp == 10
