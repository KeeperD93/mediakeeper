"""Build the achievement payload for the profile page trophy section."""
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement, UserAchievement
from models.portal.profile import UserProfile
from services.portal.achievement_defs import (
    TIER_NAMES, SECRET_THEMES, TITLE_REWARDS, SECONDARY_CATEGORIES,
    META_TARGET_CATEGORY,
)
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from services.portal.achievements_utils import _load_user_achievement_map
from services.portal.achievements_seasonal import _compute_seasonal_years


async def get_achievements_for_profile(
    db: AsyncSession, user_id: int
) -> dict:
    """
    Returns everything needed by the profile page trophy section:
    - All achievements with user progress + rarity
    - Unlocked count / total
    - Next closest achievement (urgency bar)
    """
    all_achs_raw = (await db.execute(
        select(Achievement).order_by(Achievement.sort_order)
    )).scalars().all()

    ua_map = await _load_user_achievement_map(db, user_id)

    # Hide placeholders from the profile payload so the global progression
    # percentage exposed to the UI reflects only attainable achievements.
    # Exception: keep a placeholder visible if it is already unlocked for
    # this user — admin debug unlock or any future implementation should
    # surface in the UI immediately rather than vanishing into the seal.
    unlocked_placeholder_ids = {
        ach_id for ach_id, ua in ua_map.items()
        if ua.unlocked and ach_id in PLACEHOLDER_IDS
    }
    all_achs = [
        a for a in all_achs_raw
        if a.id not in PLACEHOLDER_IDS or a.id in unlocked_placeholder_ids
    ]

    # Rarity: % of active users who unlocked each achievement
    total_users = (await db.execute(
        select(func.count(UserProfile.id)).where(
            UserProfile.account_active == True  # noqa: E712
        )
    )).scalar() or 1

    rarity_result = await db.execute(
        select(
            UserAchievement.achievement_id,
            func.count(distinct(UserAchievement.user_id)).label("cnt"),
        )
        .where(UserAchievement.unlocked == True)  # noqa: E712
        .group_by(UserAchievement.achievement_id)
    )
    rarity_map = {r.achievement_id: r.cnt for r in rarity_result.all()}

    seasonal_years = await _compute_seasonal_years(db, user_id)

    # Family → title map: "time_de_vol_6" → strip trailing "_N" → "time_de_vol".
    # Lets every tier of a family advertise the family's title reward, even
    # though only the specified tier ID actually unlocks it.
    family_titles: dict[str, str] = {}
    for ach_id, title_key in TITLE_REWARDS.items():
        family = ach_id.rsplit("_", 1)[0] if ach_id.rsplit("_", 1)[-1].isdigit() else ach_id
        family_titles[family] = title_key

    items = []
    unlocked_count = 0
    best_next = None  # closest to unlock

    for ach in all_achs:
        ua = ua_map.get(ach.id)
        is_unlocked = ua.unlocked if ua else False
        progress = ua.progress if ua else 0

        if is_unlocked:
            unlocked_count += 1

        pct = round(100 * (rarity_map.get(ach.id, 0) / total_users))
        rarity = _rarity_label(ach.tier)

        if is_unlocked:
            status = "unlocked"
        elif ach.secret and progress == 0:
            status = "secret"
        elif progress > 0:
            status = "progress"
        else:
            status = "locked"

        item = {
            "id": ach.id,
            "name_key": ach.name_key,
            "description_key": ach.description_key,
            "icon": ach.icon,
            "tier": ach.tier,
            "tier_name": TIER_NAMES.get(ach.tier, "bronze"),
            "category": ach.category,
            "xp_reward": ach.xp_reward,
            "threshold": ach.threshold,
            "progress": progress,
            "status": status,
            "unlocked_at": ua.unlocked_at.isoformat() if ua and ua.unlocked_at else None,
            "rarity_pct": pct,
            "rarity": rarity,
            "secret": ach.secret,
            "stars": ach.tier,
            "next_tier_id": ach.next_tier_id,
            "sort_order": ach.sort_order,
            "secret_theme": SECRET_THEMES.get(ach.id),
            "secondary_category": SECONDARY_CATEGORIES.get(ach.id),
            "target_category": META_TARGET_CATEGORY.get(ach.id),
            "title_reward": family_titles.get(
                ach.id.rsplit("_", 1)[0] if ach.id.rsplit("_", 1)[-1].isdigit() else ach.id
            ),
            "seasonal_years": seasonal_years.get(ach.id, []),
        }
        items.append(item)

        if not is_unlocked and progress > 0 and ach.threshold > 0:
            fill_pct = progress / ach.threshold
            if best_next is None or fill_pct > best_next["_fill"]:
                best_next = {**item, "_fill": fill_pct}

    if best_next:
        best_next.pop("_fill", None)

    return {
        "items": items,
        "unlocked_count": unlocked_count,
        "total_count": len(all_achs),
        "next_achievement": best_next,
    }


def _rarity_label(tier: int) -> str:
    """Tier-based rarity color (palier 1..6 → common..mythic).
    Decoupled from the statistical % so colors stay meaningful even
    on a small user base — relying on player count to derive rarity
    means tiny instances only ever see common/gray badges."""
    return {
        1: "common",
        2: "uncommon",
        3: "rare",
        4: "epic",
        5: "legendary",
        6: "mythic",
    }.get(tier, "common")
