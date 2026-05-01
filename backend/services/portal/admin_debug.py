"""Admin debug actions — surgical XP / level / achievement edits.

These helpers bypass the anti-abuse rules of ``grant_xp`` (daily caps,
unique-action dedup, watch percentage) so an administrator can repair
state, reward early adopters, or test trophy logic. Every operation
records a row in ``XpLedger`` (for audit) and recomputes the level
from the total XP so the cached ``UserProfile.level`` never drifts.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement, UserAchievement
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.portal.xp import MAX_LEVEL, level_from_xp, xp_for_level


logger = logging.getLogger("mediakeeper.portal.admin_debug")

ADMIN_GRANT_ACTION = "admin_grant"


async def _get_profile(db: AsyncSession, user_id: int) -> UserProfile | None:
    return (await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )).scalar_one_or_none()


async def admin_grant_xp(
    db: AsyncSession, user_id: int, amount: int, note: str | None = None,
) -> dict | None:
    """Add (or remove, when ``amount`` is negative) XP from a user.

    The grant is stamped with a unique reference so multiple admin
    edits stack up without colliding with the unique constraint.
    Returns ``{xp, level, leveled_up}`` or ``None`` if the profile is
    missing.
    """
    profile = await _get_profile(db, user_id)
    if not profile:
        return None

    delta = int(amount)
    if delta == 0:
        return {"xp": profile.xp or 0, "level": profile.level or 0, "leveled_up": False}

    ref_suffix = (note or uuid.uuid4().hex)[:48]
    entry = XpLedger(
        user_id=user_id,
        action=ADMIN_GRANT_ACTION,
        reference=f"{datetime.now(timezone.utc).timestamp()}:{ref_suffix}",
        xp=delta,
    )
    db.add(entry)

    previous_level = profile.level or 0
    profile.xp = max(0, (profile.xp or 0) + delta)
    profile.level = level_from_xp(profile.xp)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    logger.info(
        "[ADMIN_DEBUG] grant_xp user_id=%s delta=%s -> total=%s level=%s",
        user_id, delta, profile.xp, profile.level,
    )
    return {
        "xp": profile.xp,
        "level": profile.level,
        "leveled_up": profile.level > previous_level,
    }


async def admin_set_level(
    db: AsyncSession, user_id: int, level: int,
) -> dict | None:
    """Force the user to a specific level. ``profile.xp`` is bumped
    up to (and never above) the cumulative XP required for that
    level, so the level bar reads cleanly. To go down a level we
    also lower the XP to the floor of the target level."""
    profile = await _get_profile(db, user_id)
    if not profile:
        return None

    target = max(0, min(MAX_LEVEL, int(level)))
    target_xp_floor = xp_for_level(target)
    delta = target_xp_floor - (profile.xp or 0)

    entry = XpLedger(
        user_id=user_id,
        action=ADMIN_GRANT_ACTION,
        reference=f"set_level:{datetime.now(timezone.utc).timestamp()}:{uuid.uuid4().hex[:8]}",
        xp=delta,
    )
    db.add(entry)

    profile.xp = target_xp_floor
    profile.level = target
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    logger.info(
        "[ADMIN_DEBUG] set_level user_id=%s -> level=%s xp=%s",
        user_id, target, target_xp_floor,
    )
    return {"xp": profile.xp, "level": profile.level, "delta": delta}


async def admin_unlock_achievement(
    db: AsyncSession, user_id: int, achievement_id: str,
) -> dict | None:
    """Mark an achievement unlocked for the user. Idempotent."""
    achievement = await db.get(Achievement, achievement_id)
    if not achievement:
        return None

    ua = (await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement_id,
        )
    )).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if ua and ua.unlocked:
        return {"achievement_id": achievement_id, "unlocked": True, "already": True}

    if ua is None:
        ua = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            progress=achievement.threshold or 1,
            unlocked=True,
            unlocked_at=now,
        )
        db.add(ua)
    else:
        ua.unlocked = True
        ua.unlocked_at = now
        ua.progress = max(ua.progress or 0, achievement.threshold or 1)
        db.add(ua)

    await db.commit()
    logger.info(
        "[ADMIN_DEBUG] unlock_achievement user_id=%s ach=%s",
        user_id, achievement_id,
    )
    return {"achievement_id": achievement_id, "unlocked": True, "already": False}


async def admin_lock_achievement(
    db: AsyncSession, user_id: int, achievement_id: str,
) -> dict | None:
    """Reset an achievement: drop the UserAchievement row entirely so
    progression starts over. Idempotent — calling on an already-locked
    achievement returns successfully."""
    achievement = await db.get(Achievement, achievement_id)
    if not achievement:
        return None

    deleted = await db.execute(
        delete(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement_id,
        )
    )
    await db.commit()
    logger.info(
        "[ADMIN_DEBUG] lock_achievement user_id=%s ach=%s removed=%s",
        user_id, achievement_id, deleted.rowcount,
    )
    return {"achievement_id": achievement_id, "unlocked": False}


async def admin_reset_achievement_for_all(
    db: AsyncSession, achievement_id: str,
) -> dict | None:
    """Reset a specific achievement for **every** user.

    Drops every ``UserAchievement`` row for ``achievement_id`` and refunds
    the matching ``achievement_unlocked`` XP grants from ``XpLedger``.
    Each affected profile's ``xp`` / ``level`` is recomputed from the
    sum of remaining ledger entries so the cached values stay coherent.

    Used to scrub trophies that were unlocked because of a counter bug —
    after a recheck-all, only users who genuinely qualify will get them
    back.
    """
    achievement = await db.get(Achievement, achievement_id)
    if not achievement:
        return None

    ua_rows = (await db.execute(
        select(UserAchievement.user_id).where(
            UserAchievement.achievement_id == achievement_id,
            UserAchievement.unlocked == True,  # noqa: E712
        )
    )).scalars().all()
    affected_user_ids = list({uid for uid in ua_rows if uid is not None})

    deleted_ua = await db.execute(
        delete(UserAchievement).where(
            UserAchievement.achievement_id == achievement_id,
        )
    )
    deleted_ledger = await db.execute(
        delete(XpLedger).where(
            XpLedger.action == "achievement_unlocked",
            XpLedger.reference == f"ach:{achievement_id}",
        )
    )

    # Recompute xp/level for every affected profile from the surviving
    # ledger sum — the simplest authoritative source of truth.
    from sqlalchemy import func
    rebuilt = 0
    for uid in affected_user_ids:
        total = (await db.execute(
            select(func.coalesce(func.sum(XpLedger.xp), 0))
            .where(XpLedger.user_id == uid)
        )).scalar_one()
        profile = await _get_profile(db, uid)
        if profile:
            profile.xp = max(0, int(total or 0))
            profile.level = level_from_xp(profile.xp)
            db.add(profile)
            rebuilt += 1

    await db.commit()
    logger.info(
        "[ADMIN_DEBUG] reset_for_all ach=%s ua_removed=%s ledger_removed=%s "
        "profiles_rebuilt=%s",
        achievement_id, deleted_ua.rowcount, deleted_ledger.rowcount, rebuilt,
    )
    return {
        "achievement_id": achievement_id,
        "user_achievements_removed": deleted_ua.rowcount,
        "xp_ledger_removed": deleted_ledger.rowcount,
        "profiles_rebuilt": rebuilt,
    }
