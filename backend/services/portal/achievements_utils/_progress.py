"""Progression/unlock + hygiene des lines user_achievements."""
import logging
from datetime import datetime, timezone

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement, UserAchievement

logger = logging.getLogger("mediakeeper.portal.achievements")

MAX_PINNED_BADGES = 5


async def update_progress(
    db: AsyncSession,
    user_id: int,
    achievement_id: str,
    new_value: int | None = None,
    increment: int = 1,
    ua_map: dict[str, UserAchievement] | None = None,
) -> dict | None:
    """
    Set or increment progress on an achievement.
    If new_value is given, sets progress to that value (for absolute counters).
    Otherwise increments by `increment`.
    Returns unlock info if newly unlocked.
    """
    achievement = await db.get(Achievement, achievement_id)
    if not achievement:
        return None

    ua = ua_map.get(achievement_id) if ua_map is not None else None
    if ua is None and ua_map is None:
        ua = await _get_user_achievement_row(db, user_id, achievement_id)

    if not ua:
        ua = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            progress=0,
        )
        db.add(ua)
        if ua_map is not None:
            ua_map[achievement_id] = ua

    if ua.unlocked:
        return None

    if new_value is not None:
        ua.progress = new_value
    else:
        ua.progress += increment

    newly_unlocked = False
    if ua.progress >= achievement.threshold:
        ua.unlocked = True
        ua.unlocked_at = datetime.now(timezone.utc)
        newly_unlocked = True
        logger.info(f"[ACHIEVEMENT] user_id={user_id} unlocked '{achievement_id}'")

    await db.flush()

    if newly_unlocked:
        await _grant_xp(db, user_id, achievement.id, achievement.xp_reward)
        return {
            "achievement_id": achievement_id,
            "name_key": achievement.name_key,
            "icon": achievement.icon,
            "tier": achievement.tier,
            "xp_reward": achievement.xp_reward,
        }
    return None


async def _grant_xp(
    db: AsyncSession, user_id: int, achievement_id: str, amount: int
):
    from services.portal.xp import grant_xp
    await grant_xp(
        db,
        user_id,
        "achievement_unlocked",
        f"ach:{achievement_id}",
        xp_override=amount,
    )


async def _load_user_achievement_map(
    db: AsyncSession, user_id: int
) -> dict[str, UserAchievement]:
    rows = (await db.execute(
        select(UserAchievement)
        .where(UserAchievement.user_id == user_id)
        .order_by(
            UserAchievement.achievement_id,
            desc(UserAchievement.unlocked),
            desc(UserAchievement.progress),
            desc(UserAchievement.id),
        )
    )).scalars().all()

    ua_map: dict[str, UserAchievement] = {}
    duplicates = []
    for row in rows:
        if row.achievement_id in ua_map:
            duplicates.append(row)
            continue
        ua_map[row.achievement_id] = row

    if duplicates:
        for row in duplicates:
            await db.delete(row)
        await db.flush()
        logger.warning(
            "[ACHIEVEMENTS] Removed %s duplicate user_achievements rows for user_id=%s",
            len(duplicates),
            user_id,
        )

    return ua_map


async def _get_user_achievement_row(
    db: AsyncSession, user_id: int, achievement_id: str
) -> UserAchievement | None:
    return (await _load_user_achievement_map(db, user_id)).get(achievement_id)


async def _enforce_user_achievement_uniqueness(db: AsyncSession) -> None:
    try:
        rows = (await db.execute(
            select(UserAchievement)
            .order_by(
                UserAchievement.user_id,
                UserAchievement.achievement_id,
                desc(UserAchievement.unlocked),
                desc(UserAchievement.progress),
                desc(UserAchievement.id),
            )
        )).scalars().all()

        seen = set()
        removed = 0
        for row in rows:
            key = (row.user_id, row.achievement_id)
            if key in seen:
                await db.delete(row)
                removed += 1
                continue
            seen.add(key)

        if removed:
            await db.flush()
            logger.warning(
                "[ACHIEVEMENTS] Removed %s duplicate user_achievements rows before indexing",
                removed,
            )

        await db.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_achievements_user_achievement "
            "ON user_achievements (user_id, achievement_id)"
        ))
    except Exception as e:
        logger.debug(f"[ACHIEVEMENTS] uniqueness enforcement skipped: {e}")
