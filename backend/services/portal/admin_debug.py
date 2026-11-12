"""Admin debug actions — surgical XP / level / achievement edits.

These helpers bypass the anti-abuse rules of ``grant_xp`` (daily caps,
unique-action dedup, watch percentage) so an administrator can repair
state, reward early adopters, or test trophy logic. Every change of XP
records in ``XpLedger`` the gap it really made (for audit) and recomputes
the level from the total XP so the cached ``UserProfile.level`` never drifts.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement, UserAchievement
from models.portal.xp_ledger import XpLedger
from services.portal.admin_users_audit import record_audit
from services.portal.admin_users_constants import (
    ACTION_DEBUG_ACHIEVEMENT_LOCKED,
    ACTION_DEBUG_ACHIEVEMENT_RESET_ALL,
    ACTION_DEBUG_ACHIEVEMENT_UNLOCKED,
    ACTION_DEBUG_LEVEL_SET,
    ACTION_DEBUG_XP_GRANTED,
)
from services.portal.xp import (
    ACHIEVEMENT_XP_ACTION,
    MAX_LEVEL,
    MIN_LEVEL,
    achievement_xp_reference,
    level_floor_xp,
    level_from_xp,
    locked_profile,
)

logger = logging.getLogger("mediakeeper.portal.admin_debug")

ADMIN_GRANT_ACTION = "admin_grant"


async def admin_grant_xp(
    db: AsyncSession, user_id: int, amount: int, note: str | None = None,
    *, admin_user_id: int | None = None,
    ip: str | None = None, user_agent: str | None = None,
) -> dict | None:
    """Add (or remove, when ``amount`` is negative) XP from a user.

    The grant is stamped with a unique reference so multiple admin
    edits stack up without colliding with the unique constraint.
    Returns ``{xp, level, leveled_up}`` or ``None`` if the profile is
    missing.
    """
    profile = await locked_profile(db, user_id)
    if not profile:
        return None

    delta = int(amount)
    if delta == 0:
        await db.commit()  # releases the lock
        return {"xp": profile.xp or 0, "level": profile.level or MIN_LEVEL, "leveled_up": False}

    before = profile.xp or 0
    after = max(0, before + delta)
    if after != before:  # a removal below 0 takes, and records, only what the player had
        ref_suffix = (note or uuid.uuid4().hex)[:48]
        db.add(XpLedger(
            user_id=user_id,
            action=ADMIN_GRANT_ACTION,
            reference=f"{datetime.now(timezone.utc).timestamp()}:{ref_suffix}",
            xp=after - before,
        ))

    previous_level = profile.level or MIN_LEVEL
    profile.xp = after
    profile.level = level_from_xp(profile.xp)
    db.add(profile)
    await record_audit(
        db, admin_user_id=admin_user_id, target_user_id=user_id,
        action=ACTION_DEBUG_XP_GRANTED,
        payload={"delta": delta, "note": note, "xp": profile.xp, "level": profile.level},
        ip=ip, user_agent=user_agent, commit=False,
    )
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
    *, admin_user_id: int | None = None,
    ip: str | None = None, user_agent: str | None = None,
) -> dict | None:
    """Force the user to a specific level. ``profile.xp`` is set to the
    XP at which that level starts (``level_floor_xp``, 0 for level 1),
    up or down, so the level bar starts empty (full at ``MAX_LEVEL``)."""
    profile = await locked_profile(db, user_id)
    if not profile:
        return None

    target = max(MIN_LEVEL, min(MAX_LEVEL, int(level)))
    target_xp_floor = level_floor_xp(target)
    delta = target_xp_floor - (profile.xp or 0)

    if delta:  # an unchanged XP total leaves nothing for the XP history
        db.add(XpLedger(
            user_id=user_id,
            action=ADMIN_GRANT_ACTION,
            reference=f"set_level:{datetime.now(timezone.utc).timestamp()}:{uuid.uuid4().hex[:8]}",
            xp=delta,
        ))

    profile.xp = target_xp_floor
    profile.level = target
    db.add(profile)
    await record_audit(
        db, admin_user_id=admin_user_id, target_user_id=user_id,
        action=ACTION_DEBUG_LEVEL_SET,
        payload={"level": target, "delta": delta},
        ip=ip, user_agent=user_agent, commit=False,
    )
    await db.commit()
    await db.refresh(profile)

    logger.info(
        "[ADMIN_DEBUG] set_level user_id=%s -> level=%s xp=%s",
        user_id, target, target_xp_floor,
    )
    return {"xp": profile.xp, "level": profile.level, "delta": delta}


async def admin_unlock_achievement(
    db: AsyncSession, user_id: int, achievement_id: str,
    *, admin_user_id: int | None = None,
    ip: str | None = None, user_agent: str | None = None,
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

    await record_audit(
        db, admin_user_id=admin_user_id, target_user_id=user_id,
        action=ACTION_DEBUG_ACHIEVEMENT_UNLOCKED,
        payload={"achievement_id": achievement_id},
        ip=ip, user_agent=user_agent, commit=False,
    )
    await db.commit()
    logger.info(
        "[ADMIN_DEBUG] unlock_achievement user_id=%s ach=%s",
        user_id, achievement_id,
    )
    return {"achievement_id": achievement_id, "unlocked": True, "already": False}


async def admin_lock_achievement(
    db: AsyncSession, user_id: int, achievement_id: str,
    *, admin_user_id: int | None = None,
    ip: str | None = None, user_agent: str | None = None,
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
    await record_audit(
        db, admin_user_id=admin_user_id, target_user_id=user_id,
        action=ACTION_DEBUG_ACHIEVEMENT_LOCKED,
        payload={"achievement_id": achievement_id, "removed": deleted.rowcount},
        ip=ip, user_agent=user_agent, commit=False,
    )
    await db.commit()
    logger.info(
        "[ADMIN_DEBUG] lock_achievement user_id=%s ach=%s removed=%s",
        user_id, achievement_id, deleted.rowcount,
    )
    return {"achievement_id": achievement_id, "unlocked": False}


async def admin_reset_achievement_for_all(
    db: AsyncSession, achievement_id: str,
    *, admin_user_id: int | None = None,
    ip: str | None = None, user_agent: str | None = None,
) -> dict | None:
    """Reset a specific achievement for **every** user.

    Drops its ``UserAchievement`` rows and its ``achievement_unlocked``
    ledger rows. Each player loses exactly the XP those rows gave, never
    below 0: XP from before the ledger stays. Used to scrub trophies that
    were unlocked because of a counter bug — after a recheck-all, only
    users who genuinely qualify will get them back.
    """
    achievement = await db.get(Achievement, achievement_id)
    if not achievement:
        return None

    rewarded = (
        XpLedger.action == ACHIEVEMENT_XP_ACTION,
        XpLedger.reference == achievement_xp_reference(achievement_id),
    )
    # Trophy rows first and locked, as the trophy check takes them: an unlock
    # in flight ends before the list is read, and lands in it.
    rows = (await db.execute(
        select(UserAchievement.user_id, UserAchievement.unlocked.is_(True))
        .where(UserAchievement.achievement_id == achievement_id)
        .with_for_update()
    )).all()
    owners = set((await db.execute(select(XpLedger.user_id).where(*rewarded))).scalars())
    affected = sorted({uid for uid, held in rows if held} | owners)
    # Profiles before the ledger, in id order, like every other XP writer.
    profiles = [await locked_profile(db, uid) for uid in affected]
    taken = dict((await db.execute(
        select(XpLedger.user_id, func.sum(XpLedger.xp))
        .where(*rewarded, XpLedger.user_id.in_(affected))
        .group_by(XpLedger.user_id)
    )).all())
    # Only the players read above: one unlocking right now keeps the trophy and its XP.
    deleted_ua = await db.execute(delete(UserAchievement).where(
        UserAchievement.achievement_id == achievement_id,
        UserAchievement.user_id.in_(sorted({uid for uid, _ in rows} | owners)),
    ))
    deleted_ledger = await db.execute(delete(XpLedger).where(*rewarded, XpLedger.user_id.in_(affected)))

    rebuilt = 0
    for profile in filter(None, profiles):
        profile.xp = max(0, (profile.xp or 0) - int(taken.get(profile.user_id) or 0))
        profile.level = level_from_xp(profile.xp)
        rebuilt += 1

    # Multi-user mutation → no single target_user_id; the counts in the
    # payload bound the blast radius for after-the-fact review.
    await record_audit(
        db, admin_user_id=admin_user_id, target_user_id=None,
        action=ACTION_DEBUG_ACHIEVEMENT_RESET_ALL,
        payload={
            "achievement_id": achievement_id,
            "user_achievements_removed": deleted_ua.rowcount,
            "profiles_rebuilt": rebuilt,
        },
        ip=ip, user_agent=user_agent, commit=False,
    )
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
