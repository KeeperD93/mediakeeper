"""Cosmetics a player equips from their trophies: a title, an avatar effect, pinned badges."""
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from services.portal.achievement_defs import TITLE_REWARDS
from services.portal.achievement_defs_meta import META_TARGET_CATEGORY


async def unlocked_achievement_ids(db: AsyncSession, user_id: int) -> set[str]:
    rows = (await db.execute(
        select(UserAchievement.achievement_id)
        .where(UserAchievement.user_id == user_id)
        .where(UserAchievement.unlocked.is_(True))
    )).scalars().all()
    return set(rows)


def titles_from(achievement_ids: Iterable[str]) -> set[str]:
    """The title keys these trophies earn."""
    return {TITLE_REWARDS[a] for a in achievement_ids if a in TITLE_REWARDS}


def avatar_effects_from(achievement_ids: Iterable[str]) -> set[str]:
    """Each Master earns the avatar effect named after the category it masters."""
    return {META_TARGET_CATEGORY[a] for a in achievement_ids if a in META_TARGET_CATEGORY}


def stale_decoration_updates(profile: UserProfile, unlocked: set[str]) -> dict:
    """Equipped cosmetics on ``profile`` that no longer reference one of the ``unlocked``
    trophies, as a ``{column: cleaned_value}`` map (empty when nothing is stale). Pure: the
    caller decides whether to persist them or only hide them for display."""
    updates: dict = {}
    if profile.selected_title and profile.selected_title not in titles_from(unlocked):
        updates["selected_title"] = None
    if profile.avatar_effect and profile.avatar_effect not in avatar_effects_from(unlocked):
        updates["avatar_effect"] = None
    if profile.selected_badges:
        kept = [b for b in profile.selected_badges if b in unlocked]
        if len(kept) != len(profile.selected_badges):
            updates["selected_badges"] = kept or None
    return updates
