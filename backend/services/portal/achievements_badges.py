"""Pin/unpin badges on profile + global leaderboard query."""
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from services.portal.achievements_utils import (
    MAX_PINNED_BADGES,
    _load_user_achievement_map,
)
from services.portal.profile_serializers import _resolve_avatar_url


async def pin_badge(db: AsyncSession, user_id: int, achievement_id: str) -> bool:
    """Pin an unlocked achievement to profile. Max 5.

    The profile row is reloaded with ``FOR UPDATE`` before the JSON list
    is rewritten so two concurrent pin/unpin calls cannot read the same
    ``selected_badges`` snapshot and overwrite each other's edits.
    """
    ua = (await _load_user_achievement_map(db, user_id)).get(achievement_id)
    if not ua or not ua.unlocked:
        return False

    profile = (await db.execute(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .with_for_update()
    )).scalar_one_or_none()
    if not profile:
        return False

    badges = list(profile.selected_badges or [])
    if achievement_id in badges:
        # Idempotent: nothing to write, but commit to release the row lock.
        await db.commit()
        return True
    if len(badges) >= MAX_PINNED_BADGES:
        await db.commit()
        return False

    profile.selected_badges = badges + [achievement_id]
    db.add(profile)
    await db.commit()
    return True


async def unpin_badge(db: AsyncSession, user_id: int, achievement_id: str) -> bool:
    """Unpin a badge from profile. Idempotent under concurrent edits."""
    profile = (await db.execute(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .with_for_update()
    )).scalar_one_or_none()
    if not profile:
        return False

    badges = list(profile.selected_badges or [])
    if achievement_id not in badges:
        await db.commit()
        return True
    profile.selected_badges = [b for b in badges if b != achievement_id]
    db.add(profile)
    await db.commit()
    return True


async def get_leaderboard(
    db: AsyncSession, limit: int = 20
) -> list[dict]:
    """Top users by XP with achievement count."""
    result = await db.execute(
        select(UserProfile)
        .where(
            UserProfile.account_active == True,  # noqa: E712
            UserProfile.is_public == True,  # noqa: E712
            UserProfile.role != "admin",
        )
        .order_by(UserProfile.xp.desc())
        .limit(limit)
    )
    profiles = result.scalars().all()
    leaderboard = []
    for p in profiles:
        ach_count = (await db.execute(
            select(func.count(distinct(UserAchievement.achievement_id))).where(
                UserAchievement.user_id == p.user_id,
                UserAchievement.unlocked == True,  # noqa: E712
            )
        )).scalar() or 0
        leaderboard.append({
            "user_id": p.user_id,
            "display_name": p.display_name,
            "avatar_url": _resolve_avatar_url(p),
            "level": p.level,
            "xp": p.xp,
            "achievements_count": ach_count,
            "selected_badges": p.selected_badges,
            "selected_title": p.selected_title,
        })
    return leaderboard
