"""Every XP writer locks the profile before the ledger, and keeps no lock after a refusal."""
import pytest
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement, UserAchievement
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from models.user import User
from services.portal.admin_debug import admin_grant_xp, admin_reset_achievement_for_all, admin_set_level
from services.portal.xp import DAILY_REQUEST_XP_CAP, XP_TABLE, grant_xp

pytestmark = pytest.mark.asyncio


async def _profile(db: AsyncSession, name: str = "alice") -> UserProfile:
    user = User(username=name, hashed_password="x", is_active=True, must_change_password=False)
    db.add(user)
    await db.commit()
    profile = UserProfile(
        user_id=user.id, display_name=name.title(), role="viewer", account_active=True,
        source="emby", emby_user_id=f"emby-{name}",
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def _grant_elsewhere(db: AsyncSession, user_id: int, xp: int) -> None:
    """A grant committed by another session (the collector) while ``db`` holds the profile."""
    async with AsyncSession(db.bind, expire_on_commit=False) as worker:
        await grant_xp(worker, user_id, "achievement_unlocked", "ach:test-trophy", xp_override=xp)


async def _stored_and_ledger(db: AsyncSession, user_id: int) -> tuple[int, int]:
    async with AsyncSession(db.bind, expire_on_commit=False) as reader:
        stored = await reader.scalar(select(UserProfile.xp).where(UserProfile.user_id == user_id))
        ledger = await reader.scalar(
            select(func.coalesce(func.sum(XpLedger.xp), 0)).where(XpLedger.user_id == user_id)
        )
    return stored, ledger


async def test_admin_grant_keeps_the_xp_granted_meanwhile(db_session):
    profile = await _profile(db_session)
    await _grant_elsewhere(db_session, profile.user_id, 10)

    await admin_grant_xp(db_session, profile.user_id, 50, note="test")

    assert await _stored_and_ledger(db_session, profile.user_id) == (60, 60)


async def test_admin_set_level_writes_the_real_gap(db_session):
    profile = await _profile(db_session, "bob")
    await _grant_elsewhere(db_session, profile.user_id, 10)

    result = await admin_set_level(db_session, profile.user_id, 2)

    assert result["delta"] == 290
    assert await _stored_and_ledger(db_session, profile.user_id) == (300, 300)


async def _writes(db: AsyncSession, call) -> list[str]:
    """The profile reads and ledger writes ``call`` sends, in order."""
    seen: list[str] = []

    def _spy(conn, cursor, statement, params, context, executemany):
        flat = " ".join(statement.split()).upper()
        if flat.startswith(("INSERT INTO XP_LEDGER", "DELETE FROM XP_LEDGER")):
            seen.append("ledger")
        elif flat.startswith("SELECT") and "FROM USER_PROFILES" in flat:
            seen.append(f"profile {params[0]}")

    engine = db.bind.sync_engine
    event.listen(engine, "before_cursor_execute", _spy)
    try:
        await call()
    finally:
        event.remove(engine, "before_cursor_execute", _spy)
    return seen


async def test_grant_locks_the_profile_before_writing_the_ledger(db_session):
    profile = await _profile(db_session, "carol")

    seen = await _writes(db_session, lambda: grant_xp(db_session, profile.user_id, "request_created", "request:1"))

    assert seen == [f"profile {profile.user_id}", "ledger"]


async def test_reset_for_all_locks_the_profiles_in_id_order_then_rebuilds_their_xp(db_session):
    holders = [await _profile(db_session, name) for name in ("frank", "grace")]
    db_session.add(Achievement(
        id="test-trophy", category="watching", name_key="k", description_key="d", icon="Film",
        condition_type="watch_movies",
    ))
    for profile in reversed(holders):
        db_session.add(UserAchievement(user_id=profile.user_id, achievement_id="test-trophy", unlocked=True))
        db_session.add_all([
            XpLedger(user_id=profile.user_id, action="achievement_unlocked", reference="ach:test-trophy", xp=20),
            XpLedger(user_id=profile.user_id, action="request_created", reference="request:1", xp=5),
        ])
    await db_session.commit()

    seen = await _writes(db_session, lambda: admin_reset_achievement_for_all(db_session, "test-trophy"))

    assert seen == [f"profile {p.user_id}" for p in holders] + ["ledger"]
    for profile in holders:
        assert await _stored_and_ledger(db_session, profile.user_id) == (5, 5)


async def test_a_refused_grant_ends_its_transaction_and_keeps_the_pending_work(db_session):
    profile = await _profile(db_session, "dave")
    assert await grant_xp(db_session, profile.user_id, "request_created", "request:1")

    profile.bio = "Test bio"  # the caller's pending work, flushed by the lock
    assert await grant_xp(db_session, profile.user_id, "request_created", "request:1") is None

    assert not db_session.in_transaction()
    async with AsyncSession(db_session.bind) as reader:
        assert await reader.scalar(select(UserProfile.bio).where(UserProfile.id == profile.id)) == "Test bio"


async def test_the_daily_request_cap_still_holds_and_releases_the_lock(db_session):
    profile = await _profile(db_session, "erin")
    allowed = DAILY_REQUEST_XP_CAP // XP_TABLE["request_created"]
    for i in range(allowed):
        assert await grant_xp(db_session, profile.user_id, "request_created", f"request:{i}")

    assert await grant_xp(db_session, profile.user_id, "request_created", "request:extra") is None

    assert not db_session.in_transaction()
    assert await _stored_and_ledger(db_session, profile.user_id) == (DAILY_REQUEST_XP_CAP,) * 2
