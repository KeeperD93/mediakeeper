"""Simulate, then apply, a watch XP recalculation.

Simulating plans every player in a read-only transaction, then rolls it back. Applying
plans the same way and refuses a plan the admin has not seen, backs up (a backup that
fails or lacks a part refuses the apply), then writes every player in one transaction:
the profiles of the scope locked in id order, the plan made again under the locks and
checked once more, each player's rows replaced and journaled, one commit. An error while
writing leaves nothing written; the log names the backup, and so does a failure journal
unless writing it fails too.
"""
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from constants.watch_xp_recalc import (
    ALREADY_RUNNING,
    APPLY_FAILED,
    BACKUP_INCOMPLETE,
    PLAN_CHANGED,
)
from core.errors import CodedError
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.backup.create import create_backup
from services.portal.achievements_utils import _coerce_utc
from services.portal.admin_users_audit import record_audit
from services.portal.admin_users_constants import (
    ACTION_DEBUG_WATCH_XP_RECALC,
    ACTION_DEBUG_WATCH_XP_RECALC_PLAYER,
)
from services.portal.daily_digest import invalidate_all
from services.portal.recalc_lock import RECALC_LOCK
from services.portal.xp import level_from_xp, locked_profile

from ._context import build_context
from ._months import month_changes
from ._plan import PlayerPlan, plan_all
from ._summary import fingerprint, summarize

logger = logging.getLogger("mediakeeper.portal.watch_xp_recalc")

BACKUP_LABEL = "watch_xp_recalc"


class WatchXpRecalcRefused(CodedError):
    """Nothing of the plan is written; ``code`` tells the client why."""


@asynccontextmanager
async def _read_only(db: AsyncSession) -> AsyncIterator[None]:
    await db.commit()  # what the request read so far; SET TRANSACTION must come first
    if db.get_bind().dialect.name == "postgresql":
        await db.execute(text("SET TRANSACTION READ ONLY"))
    try:
        yield
    finally:
        await db.rollback()


async def simulate_watch_xp_recalc(db: AsyncSession) -> dict:
    async with _read_only(db):
        ctx = await build_context(db)
        plan = await plan_all(db, ctx)
        months = await month_changes(db, ctx, plan)
        changed = [player.user_id for player in plan.players if player.changed]
        names = dict((await db.execute(
            select(UserProfile.user_id, UserProfile.display_name).where(UserProfile.user_id.in_(changed))
        )).all())
    return summarize(ctx, plan, months, names)


def _iso(moment: datetime | None) -> str | None:
    utc = _coerce_utc(moment)
    return utc.isoformat() if utc else None


async def _write_player(db: AsyncSession, plan: PlayerPlan, profile: UserProfile, audit: dict) -> None:
    """Replace the player's rows; the journal keeps what undoing them would need."""
    # What the deletion really took, read back by the deletion itself.
    taken = (await db.execute(
        delete(XpLedger).where(XpLedger.id.in_([row.id for row in plan.deleted]))
        .returning(XpLedger.action, XpLedger.reference, XpLedger.xp, XpLedger.created_at)
    )).all() if plan.deleted else []
    db.add_all(
        XpLedger(user_id=plan.user_id, action=t.action, reference=t.reference, xp=t.xp, created_at=t.at)
        for t in plan.inserted
    )
    xp, level = profile.xp or 0, profile.level
    profile.xp = max(0, xp - sum(row.xp for row in taken) + sum(t.xp for t in plan.inserted))
    profile.level = level_from_xp(profile.xp)
    await record_audit(
        db, target_user_id=plan.user_id, action=ACTION_DEBUG_WATCH_XP_RECALC_PLAYER,
        payload={
            "xp": [xp, profile.xp],
            "level": [level, profile.level],
            "undo": {
                "deleted": [
                    {"action": row.action, "reference": row.reference, "xp": row.xp, "created_at": _iso(row.created_at)}
                    for row in taken
                ],
                "inserted": [t.reference for t in plan.inserted],
            },
        },
        commit=False, **audit,
    )


async def _write(db: AsyncSession, as_of: datetime, plan: str, backup: str, audit: dict) -> dict:
    ctx = await build_context(db, as_of)
    # Profiles before the ledger, in id order, like every XP writer: a gain made meanwhile
    # waits for the commit. An account created after this list is not written.
    profiles = {user_id: await locked_profile(db, user_id) for user_id in sorted(ctx.scope)}
    found = await plan_all(db, ctx)
    if fingerprint(ctx, found) != plan:
        raise WatchXpRecalcRefused(PLAN_CHANGED)
    changed = [player for player in found.players if player.changed]
    for player in changed:
        await _write_player(db, player, profiles[player.user_id], audit)
    applied = {
        "players": len(changed),
        "rows_deleted": sum(len(player.deleted) for player in changed),
        "rows_inserted": sum(len(player.inserted) for player in changed),
    }
    await record_audit(
        db, target_user_id=None, action=ACTION_DEBUG_WATCH_XP_RECALC,
        payload={"as_of": _iso(as_of), "plan": plan, "backup": backup, **applied},
        commit=False, **audit,
    )
    await db.commit()
    return applied


async def _journal_failure(db: AsyncSession, payload: dict, audit: dict) -> None:
    """Take the writing back, then journal the failure. A lost connection fails both: the
    apply is refused as failed all the same, and the log has already named the backup."""
    try:
        await db.rollback()
        await record_audit(
            db, target_user_id=None, action=ACTION_DEBUG_WATCH_XP_RECALC, payload=payload,
            commit=True, **audit,
        )
    except Exception:
        logger.exception("[WATCH_XP_RECALC] failure journal not written")


async def apply_watch_xp_recalc(
    db: AsyncSession, *, as_of: datetime, plan: str,
    admin_user_id: int, ip: str | None, user_agent: str | None,
) -> dict:
    """Apply the plan the admin saw: ``as_of`` and the print of the simulation."""
    if RECALC_LOCK.locked():
        raise WatchXpRecalcRefused(ALREADY_RUNNING)
    async with RECALC_LOCK:
        async with _read_only(db):
            ctx = await build_context(db, as_of)
            seen = await plan_all(db, ctx)
        if fingerprint(ctx, seen) != plan:
            raise WatchXpRecalcRefused(PLAN_CHANGED)
        if not any(player.changed for player in seen.players):
            return {"plan": plan, "backup": None, "applied": {"players": 0, "rows_deleted": 0, "rows_inserted": 0}}

        try:
            backup = await create_backup(db, label=BACKUP_LABEL)
        except Exception as exc:
            logger.exception("[WATCH_XP_RECALC] backup failed: nothing applied")
            raise WatchXpRecalcRefused(BACKUP_INCOMPLETE) from exc
        name = backup.path.name
        logger.info("[WATCH_XP_RECALC] backup %s made before applying", name)
        if not backup.complete:
            logger.error("[WATCH_XP_RECALC] backup %s lacks %s: nothing applied", name, backup.failed)
            raise WatchXpRecalcRefused(BACKUP_INCOMPLETE)

        audit = {"admin_user_id": admin_user_id, "ip": ip, "user_agent": user_agent}
        try:
            applied = await _write(db, ctx.as_of, plan, name, audit)
        except WatchXpRecalcRefused:
            await db.rollback()
            raise
        except Exception as exc:
            logger.exception("[WATCH_XP_RECALC] apply failed, nothing written; backup %s", name)
            await _journal_failure(
                db, {"as_of": _iso(ctx.as_of), "plan": plan, "backup": name, "failed": True}, audit,
            )
            raise WatchXpRecalcRefused(APPLY_FAILED) from exc
        invalidate_all()
        logger.info("[WATCH_XP_RECALC] applied: %s, backup %s", applied, name)
        return {"plan": plan, "backup": name, "applied": applied}
