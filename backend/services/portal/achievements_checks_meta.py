"""Meta-achievement checker — unlocks a meta when every non-excluded
achievement of its target category is itself unlocked.

Run AFTER all standard/secret checks in the same transaction so any tier
unlocked during the current call is taken into account.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement, UserAchievement
from services.portal.achievement_defs import (
    META_TARGET_CATEGORY,
    achievements_for_category,
)
from services.portal.achievements_utils import update_progress


async def check_meta(
    db: AsyncSession,
    by_type: dict[str, list[Achievement]],
    user_id: int,
    ua_map: dict[str, UserAchievement],
    unlocked_ids: set[str],
    **_: object,
) -> list[dict]:
    """For each meta achievement, count how many non-excluded trophies of
    its target category are unlocked. Unlock the meta when all are."""
    metas = by_type.get("meta", [])
    if not metas:
        return []

    unlocks: list[dict] = []
    for meta_ach in metas:
        target = META_TARGET_CATEGORY.get(meta_ach.id)
        if not target:
            continue
        required_ids = achievements_for_category(target)
        if not required_ids:
            continue
        done = sum(1 for r in required_ids if r in unlocked_ids)
        # update_progress unlocks when progress >= threshold, so we align
        # the threshold to the actual required count (set at seed time).
        result = await update_progress(db, user_id, meta_ach.id, new_value=done, ua_map=ua_map)
        if result:
            unlocks.append(result)
    return unlocks
