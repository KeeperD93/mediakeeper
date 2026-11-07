"""A trophy row another check committed meanwhile is taken over, not inserted twice."""
import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError

from models.portal.achievement import Achievement, UserAchievement
from models.portal.xp_ledger import XpLedger
from services.portal.achievements_utils import (
    _load_user_achievement_map,
    update_progress,
)
from tests._portal_profile_helpers import make_portal_user

TROPHY = "test_trophy"


async def _player_with_stale_map(db, *, committed_meanwhile: dict | None):
    """A player whose map was read before another check committed ``committed_meanwhile``."""
    user, _ = await make_portal_user(db, username="alice")
    db.add(Achievement(
        id=TROPHY, category="watch", name_key="k", description_key="d", icon="i",
        condition_type="probe", threshold=1, xp_reward=10,
    ))
    await db.commit()
    ua_map = await _load_user_achievement_map(db, user.id)
    if committed_meanwhile is not None:
        await db.execute(insert(UserAchievement).values(
            user_id=user.id, achievement_id=TROPHY, notified=False, **committed_meanwhile,
        ))
        await db.commit()
    return user.id, ua_map


async def _rows(db, user_id: int) -> int:
    return await db.scalar(
        select(func.count()).select_from(UserAchievement).where(UserAchievement.user_id == user_id)
    )


async def _xp_grants(db, user_id: int) -> int:
    return await db.scalar(select(func.count()).select_from(XpLedger).where(XpLedger.user_id == user_id))


@pytest.mark.asyncio
async def test_progress_carries_on_from_the_row_committed_meanwhile(db_session):
    user_id, ua_map = await _player_with_stale_map(
        db_session, committed_meanwhile={"progress": 0, "unlocked": False},
    )

    unlock = await update_progress(db_session, user_id, TROPHY, new_value=1, ua_map=ua_map)

    assert unlock["achievement_id"] == TROPHY
    assert ua_map[TROPHY].unlocked is True
    assert await _rows(db_session, user_id) == 1
    assert await _xp_grants(db_session, user_id) == 1


@pytest.mark.asyncio
async def test_a_trophy_unlocked_meanwhile_is_not_unlocked_again(db_session):
    user_id, ua_map = await _player_with_stale_map(
        db_session, committed_meanwhile={"progress": 1, "unlocked": True},
    )

    assert await update_progress(db_session, user_id, TROPHY, new_value=1, ua_map=ua_map) is None
    assert await _rows(db_session, user_id) == 1
    assert await _xp_grants(db_session, user_id) == 0


@pytest.mark.asyncio
async def test_an_insert_that_is_no_duplicate_still_fails_and_leaves_the_session_usable(db_session):
    user_id, _ = await _player_with_stale_map(db_session, committed_meanwhile=None)
    ua_map: dict = {}

    # No such account: the foreign key refuses the row and there is nothing to take over.
    with pytest.raises(IntegrityError):
        await update_progress(db_session, user_id + 1000, TROPHY, new_value=1, ua_map=ua_map)

    assert ua_map == {}
    assert await _rows(db_session, user_id) == 0
