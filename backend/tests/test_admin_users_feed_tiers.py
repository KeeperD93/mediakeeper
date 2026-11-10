"""The trophy tab of the admin drawer names the tiers like the rest of the app."""
import pytest

from models.portal.achievement import UserAchievement
from services.portal.achievement_defs import ACHIEVEMENT_DEFS
from services.portal.achievements import seed_achievements
from services.portal.admin_users_feed import list_user_trophies
from tests._portal_profile_helpers import make_portal_user


@pytest.mark.asyncio
async def test_the_highest_tiers_keep_their_names(db_session):
    await seed_achievements(db_session)
    user, _ = await make_portal_user(db_session, username="alice")
    by_tier = {definition["tier"]: definition["id"] for definition in ACHIEVEMENT_DEFS}
    for achievement_id in by_tier.values():
        db_session.add(UserAchievement(user_id=user.id, achievement_id=achievement_id, progress=1, unlocked=True))
    await db_session.commit()

    trophies = (await list_user_trophies(db_session, user.id))["unlocked"]

    assert {t["tier"]: t["tier_name"] for t in trophies} == {
        1: "bronze", 2: "silver", 3: "gold", 4: "platinum", 5: "mythic", 6: "supreme",
    }
