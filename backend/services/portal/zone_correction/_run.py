"""Simulate, then apply, the correction of the trophies the UTC clock gave wrongly.

Simulating plans every player in a read-only transaction, then rolls it back. Applying
plans the same way, refuses a plan the admin has not seen, backs up, then plans each
player again in their own transaction, under the lock of their profile, and writes that
plan: a player is corrected entirely or not at all, and a second run finds nothing left.
"""
import asyncio
import logging

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from constants.zone_correction import ALREADY_RUNNING, BACKUP_INCOMPLETE, PLAN_CHANGED
from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.backup.create import create_backup
from services.portal.admin_users_audit import record_audit
from services.portal.admin_users_constants import (
    ACTION_DEBUG_ZONE_CORRECTION,
    ACTION_DEBUG_ZONE_CORRECTION_PLAYER,
)
from services.portal.daily_digest import invalidate_cache
from services.portal.xp import ACHIEVEMENT_XP_ACTION, achievement_xp_reference, level_from_xp

from ._context import Context, ZoneCorrectionRefused, build_context
from ._plan import PlayerPlan, plan_all, plan_player
from ._summary import summarize

logger = logging.getLogger("mediakeeper.portal.zone_correction")

BACKUP_LABEL = "zone_correction"
# One web process serves the admin: a second apply waits for nothing, it is refused.
_apply_lock = asyncio.Lock()


def _is_postgres(db: AsyncSession) -> bool:
    return db.get_bind().dialect.name == "postgresql"


async def _plan_read_only(db: AsyncSession) -> tuple[Context, list[PlayerPlan], int]:
    await db.commit()  # what the request read so far; SET TRANSACTION must come first
    if _is_postgres(db):
        await db.execute(text("SET TRANSACTION READ ONLY"))
    try:
        ctx = await build_context(db)
        plans, failed = await plan_all(db, ctx)
    finally:
        await db.rollback()
    return ctx, plans, failed


async def simulate_zone_correction(db: AsyncSession) -> dict:
    ctx, plans, failed = await _plan_read_only(db)
    return summarize(ctx, plans, failed)


async def _apply_player(
    db: AsyncSession, ctx: Context, user_id: int, audit: dict,
) -> PlayerPlan | None:
    """Plan and write one player in one transaction; ``None`` when nothing was left to take."""
    stmt = (
        select(UserProfile).where(UserProfile.user_id == user_id)
        .execution_options(populate_existing=True)
    )
    if _is_postgres(db):
        stmt = stmt.with_for_update()
    profile = (await db.execute(stmt)).scalar_one_or_none()
    plan = await plan_player(db, ctx, profile) if profile else None
    if plan is None or not plan.removed:
        await db.rollback()
        return None

    for achievement_id, progress in plan.removed.items():
        await db.execute(
            update(UserAchievement)
            .where(UserAchievement.user_id == user_id, UserAchievement.achievement_id == achievement_id)
            .values(unlocked=False, unlocked_at=None, progress=progress)
            .execution_options(synchronize_session="fetch")
        )
    # What the deletion really took, not what was read before the lock.
    plan.xp_removed = sum((await db.execute(
        delete(XpLedger)
        .where(
            XpLedger.user_id == user_id,
            XpLedger.action == ACHIEVEMENT_XP_ACTION,
            XpLedger.reference.in_([achievement_xp_reference(a) for a in plan.removed]),
        )
        .returning(XpLedger.xp)
    )).scalars().all())
    profile.xp = plan.xp_after
    profile.level = level_from_xp(profile.xp)
    for column, value in plan.decorations.items():
        setattr(profile, column, value)
    await record_audit(
        db, target_user_id=user_id, action=ACTION_DEBUG_ZONE_CORRECTION_PLAYER,
        payload={
            "removed": sorted(plan.direct),
            "cascade": sorted(plan.cascade),
            "xp_removed": plan.xp - plan.xp_after,
            "level": [plan.level, profile.level],
            "decorations": sorted(plan.decorations),
        },
        commit=False, **audit,
    )
    await db.commit()
    invalidate_cache(user_id)
    return plan


async def apply_zone_correction(
    db: AsyncSession, *, timezone: str, plan: str,
    admin_user_id: int, ip: str | None, user_agent: str | None,
) -> dict:
    if _apply_lock.locked():
        raise ZoneCorrectionRefused(ALREADY_RUNNING)
    async with _apply_lock:
        ctx, plans, failed = await _plan_read_only(db)
        summary = summarize(ctx, plans, failed)
        if (timezone, plan) != (summary["timezone"], summary["plan"]):
            raise ZoneCorrectionRefused(PLAN_CHANGED)
        targets = [p.user_id for p in plans if p.removed]
        if not targets:
            return {**summary, "backup": None, "applied": {"players": 0, "removed": 0, "xp_removed": 0, "failed": 0}}

        backup = await create_backup(db, label=BACKUP_LABEL)
        if not backup.complete:
            logger.error("[ZONE_CORRECTION] backup %s lacks %s: nothing applied", backup.path.name, backup.failed)
            raise ZoneCorrectionRefused(BACKUP_INCOMPLETE)

        audit = {"admin_user_id": admin_user_id, "ip": ip, "user_agent": user_agent}
        done: list[PlayerPlan] = []
        errors = 0
        for user_id in targets:
            try:
                if applied := await _apply_player(db, ctx, user_id, audit):
                    done.append(applied)
            except Exception:
                await db.rollback()
                logger.exception("[ZONE_CORRECTION] player not corrected", extra={"user_id": user_id})
                errors += 1
        applied = {
            "players": len(done),
            "removed": sum(len(p.removed) for p in done),
            "xp_removed": sum(p.xp - p.xp_after for p in done),
            "failed": errors,
        }
        await record_audit(
            db, target_user_id=None, action=ACTION_DEBUG_ZONE_CORRECTION,
            payload={
                "timezone": ctx.zone_name, "zone_saved_at": summary["zone_saved_at"],
                "plan": summary["plan"], "backup": backup.path.name, **applied,
            },
            commit=True, **audit,
        )
        logger.info("[ZONE_CORRECTION] applied: %s, backup %s", applied, backup.path.name)
        return {**summary, "backup": backup.path.name, "applied": applied}
