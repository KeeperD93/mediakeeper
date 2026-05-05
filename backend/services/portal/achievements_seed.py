"""Seed achievement definitions into the database on startup."""
import logging
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement
from services.portal.achievement_defs import (
    ACHIEVEMENT_DEFS,
    META_TARGET_CATEGORY,
    achievements_for_category,
)
from services.portal.achievements_utils import _enforce_user_achievement_uniqueness
from services.portal.achievements_validation import collect_violations

logger = logging.getLogger("mediakeeper.portal.achievements")


def _is_strict_environment() -> bool:
    """Catalogue drift fails the boot in dev/test, but only logs in prod.

    Reasoning: a production instance should not refuse to start because of
    a typo in a future migration — the runtime can keep serving with the
    other definitions. Dev and CI catch the typo loudly so it never ships.
    """
    env = (os.environ.get("ENV") or os.environ.get("ENVIRONMENT") or "").lower()
    if env in ("prod", "production"):
        return False
    return True


def _validate_definitions() -> None:
    """Inspect the catalogue and either raise (strict) or log (lax)."""
    violations = collect_violations()
    if not violations:
        return
    bullets = "\n  - ".join(violations)
    if _is_strict_environment():
        raise ValueError(
            f"achievement catalogue drift detected:\n  - {bullets}"
        )
    logger.error(
        "[ACHIEVEMENTS] catalogue drift (continuing in lax mode):\n  - %s",
        bullets,
    )
_ACHIEVEMENT_DB_FIELDS = frozenset(Achievement.__table__.columns.keys())
_ACHIEVEMENT_MUTABLE_FIELDS = tuple(
    field for field in _ACHIEVEMENT_DB_FIELDS if field not in {"id", "next_tier_id"}
)


async def seed_achievements(db: AsyncSession):
    """Insert or update achievement definitions. Safe to call on every startup."""
    # Refuse to seed a drifted catalogue in dev/test — the same diagnostics
    # the pytest meta-test uses, so CI and runtime agree on what "consistent"
    # means. Production stays lax to avoid bricking a deploy on a typo.
    _validate_definitions()

    # Resolve meta thresholds from the current category contents so the
    # unlock condition always matches reality (regardless of added/removed
    # trophies). Overrides the placeholder threshold declared in META_DEFS.
    for d in ACHIEVEMENT_DEFS:
        if d.get("condition_type") == "meta":
            target = META_TARGET_CATEGORY.get(d["id"])
            if target:
                d["threshold"] = max(1, len(achievements_for_category(target)))
    logger.info("[ACHIEVEMENTS] Starting seed (%d definitions)...", len(ACHIEVEMENT_DEFS))

    existing_ids = set()
    result = await db.execute(select(Achievement.id))
    for row in result.scalars().all():
        existing_ids.add(row)
    logger.info("[ACHIEVEMENTS] Found %d existing achievements in DB", len(existing_ids))

    # Pass 1: insert/update WITHOUT next_tier_id to avoid FK ordering issues
    count_new = 0
    for d in ACHIEVEMENT_DEFS:
        if d["id"] in existing_ids:
            ach = await db.get(Achievement, d["id"])
            if ach:
                for field in _ACHIEVEMENT_MUTABLE_FIELDS:
                    if field in d:
                        setattr(ach, field, d[field])
        else:
            row_data = {
                field: value
                for field, value in d.items()
                if field in _ACHIEVEMENT_DB_FIELDS and field != "next_tier_id"
            }
            row_data["next_tier_id"] = None
            ach = Achievement(**row_data)
            db.add(ach)
            count_new += 1

    await db.commit()

    # Pass 2: set next_tier_id now that all rows exist
    for d in ACHIEVEMENT_DEFS:
        if d.get("next_tier_id"):
            ach = await db.get(Achievement, d["id"])
            if ach and ach.next_tier_id != d["next_tier_id"]:
                ach.next_tier_id = d["next_tier_id"]

    await db.commit()

    # Pass 3: prune every achievement whose ID is no longer declared in
    # ACHIEVEMENT_DEFS. Covers meta, standard, and secret rows — keeps
    # dev DBs aligned when a slug is renamed or retired. Post-v1.0 any
    # typo in ACHIEVEMENT_DEFS would still nuke the wrong row on boot,
    # so revisit this policy once the DB is frozen.
    current_ids = {d["id"] for d in ACHIEVEMENT_DEFS}
    result = await db.execute(select(Achievement.id))
    db_ids = set(result.scalars().all())
    stale = db_ids - current_ids
    if stale:
        from models.portal.achievement import UserAchievement
        from sqlalchemy import delete as sa_delete
        await db.execute(sa_delete(UserAchievement).where(UserAchievement.achievement_id.in_(stale)))
        await db.execute(sa_delete(Achievement).where(Achievement.id.in_(stale)))
        await db.commit()
        logger.info("[ACHIEVEMENTS] Pruned %d stale achievements: %s", len(stale), sorted(stale))

    logger.info("[ACHIEVEMENTS] Seed complete: %d new, %d updated", count_new, len(existing_ids))

    await _enforce_user_achievement_uniqueness(db)
