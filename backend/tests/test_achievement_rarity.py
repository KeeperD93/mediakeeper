"""Trophy rarity on the profile page counts the accounts that may earn.

Both sides of the share (unlocks and players) follow the earning rule, so a
deactivated, local or unlinked account keeps its trophies without skewing
the rarity, and the share never goes past 100 %.
"""
import pytest

from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from models.user import User
from services.portal.achievements import get_achievements_for_profile, seed_achievements
from services.portal.admin_users_constants import SOURCE_EMBY, SOURCE_LOCAL


async def _player(
    db, username: str, *, is_active: bool = True, account_active: bool = True,
    source: str = SOURCE_EMBY, linked: bool = True,
) -> int:
    user = User(username=username, hashed_password="x", is_active=is_active)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    db.add(UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        source=source,
        account_active=account_active,
        emby_user_id=f"EMBY-{username}" if linked else None,
    ))
    await db.commit()
    return user.id


async def _unlock(db, user_ids: list[int], achievement_id: str) -> None:
    for user_id in user_ids:
        db.add(UserAchievement(
            user_id=user_id, achievement_id=achievement_id, progress=1, unlocked=True,
        ))
    await db.commit()


def _rarity(payload: dict, achievement_id: str) -> int:
    return next(item["rarity_pct"] for item in payload["items"] if item["id"] == achievement_id)


@pytest.mark.asyncio
async def test_rarity_counts_only_the_accounts_that_may_earn(db_session):
    await seed_achievements(db_session)
    alice = await _player(db_session, "alice")
    bob = await _player(db_session, "bob", account_active=False)  # never activated, still earns
    carol = await _player(db_session, "carol", is_active=False)  # deactivated
    dave = await _player(db_session, "dave", source=SOURCE_LOCAL, linked=False)  # local
    await _unlock(db_session, [alice, bob, carol, dave], "movie_buff_1")
    await _unlock(db_session, [alice, carol, dave], "movie_buff_2")

    payload = await get_achievements_for_profile(db_session, alice)

    assert _rarity(payload, "movie_buff_1") == 100
    assert _rarity(payload, "movie_buff_2") == 50
    assert all(0 <= item["rarity_pct"] <= 100 for item in payload["items"])


@pytest.mark.asyncio
async def test_rarity_is_zero_without_any_account_that_may_earn(db_session):
    await seed_achievements(db_session)
    dave = await _player(db_session, "dave", source=SOURCE_LOCAL, linked=False)
    await _unlock(db_session, [dave], "movie_buff_1")

    payload = await get_achievements_for_profile(db_session, dave)

    assert _rarity(payload, "movie_buff_1") == 0
