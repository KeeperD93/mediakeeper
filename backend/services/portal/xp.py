"""
XP (Experience Points) service for the Portal gamification system.

Direct grants (this module):
  - watch_movie:          10 XP  (Movie items only, ≥85% runtime, cooldown 24h)
  - watch_episode:         3 XP  (Episode items only, ≥85% runtime, cooldown 24h)
  - daily_login:           2 XP  (1x per calendar day)
  - request_created:       5 XP  (max 5/day)
  - achievement_unlocked: 20-100 (one-time per achievement, amount = ach.xp_reward)

Series completion, request approvals, login streaks and event participation
are rewarded through the achievement system (``completionist_*``,
``ambassador_*``, ``streak_days``, ``events_created``…) — they are NOT
granted by ``grant_xp`` directly.

Anti-abuse:
  - Unique constraint (user_id, action, reference) prevents double grants
  - Watch XP requires ≥85% of runtime AND item type Movie/Episode
  - Watched duration is clamped to runtime (pauses can't inflate the ratio)
  - No daily cap on watch XP (if you watch 10h, you earned it)
  - Daily cap on request XP: 25 XP/day (5 requests)
  - Cooldown: same item can't grant XP within 24h

Level curve (quadratic):
  XP_for_level(n) = 50 * n * (n + 1)
  Level 5   =     1,500 XP  (~2 weeks)
  Level 10  =     5,500 XP  (~2 months)
  Level 20  =    21,000 XP  (~6 months)
  Level 30  =    46,500 XP  (~1.5 years)
  Level 40  =    82,000 XP  (~3 years)
  Level 50  =   127,500 XP  (~5 years, max)
"""
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from models.portal.xp_ledger import XpLedger
from models.portal.profile import UserProfile
from services.portal._watch_threshold import WATCHED_THRESHOLD

logger = logging.getLogger("mediakeeper.portal.xp")

MAX_LEVEL = 50
DAILY_REQUEST_XP_CAP = 25
MIN_WATCH_PERCENT = WATCHED_THRESHOLD
WATCH_XP_ITEM_TYPES = {"Movie", "Episode"}  # Trailers, MusicVideo, LiveTV…
                                            # are deliberately excluded.

# XP amounts per action.
# `achievement_unlocked` is omitted on purpose — its amount is supplied by
# the caller via ``xp_override`` (each achievement carries its own reward).
XP_TABLE = {
    "watch_movie": 10,
    "watch_episode": 3,
    "daily_login": 2,
    "request_created": 5,
}


def xp_for_level(level: int) -> int:
    """Total cumulative XP needed to reach a given level."""
    return 50 * level * (level + 1)


def level_from_xp(total_xp: int) -> int:
    """Compute level from total cumulative XP."""
    level = 0
    while level < MAX_LEVEL and xp_for_level(level + 1) <= total_xp:
        level += 1
    return level


async def grant_xp(
    db: AsyncSession,
    user_id: int,
    action: str,
    reference: str,
    xp_override: int | None = None,
) -> dict | None:
    """
    Attempt to grant XP for an action. Returns the grant details if
    successful, or None if blocked by anti-abuse rules.

    The unique constraint (user_id, action, reference) is the primary
    dedup mechanism — if the exact same grant was already recorded,
    the INSERT fails silently and we return None.
    """
    base_xp = xp_override if xp_override is not None else XP_TABLE.get(action, 0)
    if base_xp <= 0:
        return None

    # --- Apply active XP boost multipliers (Christmas, Halloween, etc.) ---
    from services.portal.xp_boost import get_active_multiplier
    multiplier = await get_active_multiplier(db, action)
    xp_amount = int(round(base_xp * multiplier)) if multiplier != 1.0 else base_xp

    # --- Daily caps ---
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # No daily cap on watch XP — if someone watches 10h of movies,
    # they earned it. Anti-abuse is handled by the 85% runtime check
    # and the 24h cooldown per item in grant_watch_xp().

    if action == "request_created":
        today_req_xp = await _daily_xp_sum(db, user_id, today_start,
                                            ("request_created",))
        if today_req_xp >= DAILY_REQUEST_XP_CAP:
            return None

    # --- Insert (dedup via unique constraint) ---
    # The INSERT runs inside a SAVEPOINT so a duplicate (user_id, action,
    # reference) trips the unique constraint without invalidating the
    # outer transaction — callers (e.g. ``update_request_status``) keep
    # the work they had pending in the same session.
    try:
        async with db.begin_nested():
            db.add(XpLedger(
                user_id=user_id,
                action=action,
                reference=reference,
                xp=xp_amount,
            ))
            await db.flush()
    except IntegrityError:
        logger.debug("[XP] duplicate blocked: user=%s action=%s ref=%s", user_id, action, reference)
        return None

    # --- Update profile XP + level (row-locked to prevent concurrent-grant loss) ---
    profile = (await db.execute(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .with_for_update()
    )).scalar_one_or_none()

    leveled_up = False
    if profile:
        profile.xp = (profile.xp or 0) + xp_amount
        new_level = level_from_xp(profile.xp)
        leveled_up = new_level > (profile.level or 0)
        profile.level = new_level
        db.add(profile)

    await db.commit()

    result = {
        "action": action,
        "xp": xp_amount,
        "total_xp": profile.xp if profile else xp_amount,
        "level": profile.level if profile else 1,
        "leveled_up": leveled_up,
    }
    logger.info("[XP] granted %s XP to user=%s for %s ref=%s", xp_amount, user_id, action, reference)
    return result


async def grant_watch_xp(
    db: AsyncSession,
    user_id: int,
    item_id: str,
    item_type: str,
    duration_seconds: int,
    runtime_ticks: int | None,
) -> dict | None:
    """
    Grant XP for watching content. A single rule: ≥85% of the item
    runtime watched, plus a 24h cooldown per item.

    ``runtime_ticks`` is the Emby runtime in 100-nanosecond ticks.
    If unavailable (live streams, badly tagged items…), XP is skipped —
    there's no time-based fallback so the rule stays uniform.
    """
    if not item_id or not user_id:
        return None

    # --- Item type whitelist ---
    # Without this, trailers, MusicVideo, LiveTV recordings, etc. would
    # earn ``watch_episode`` XP (3 XP) just for being played to 85%, which
    # is a trivial farm vector.
    if item_type not in WATCH_XP_ITEM_TYPES:
        logger.debug(
            "[XP] item_type=%r not eligible: "
            "user=%s item=%s — XP skipped",
            item_type, user_id, item_id,
        )
        return None

    # --- Minimum watch check (85% of runtime, no fallback) ---
    if not runtime_ticks or runtime_ticks <= 0:
        logger.debug(
            "[XP] no runtime: user=%s item=%s — XP skipped", user_id, item_id
        )
        return None
    runtime_seconds = runtime_ticks / 10_000_000
    # Clamp the reported duration to the item's runtime: a long pause
    # inflates ``wall_duration`` (callers pass max(wall, position)) and
    # would otherwise let someone earn XP without actually watching.
    effective_duration = min(duration_seconds, runtime_seconds)
    watch_percent = effective_duration / runtime_seconds
    if watch_percent < MIN_WATCH_PERCENT:
        logger.debug(
            "[XP] watch too short: user=%s item=%s "
            "%.0f%% < %.0f%%",
            user_id, item_id, watch_percent * 100, MIN_WATCH_PERCENT * 100,
        )
        return None

    # --- 24h cooldown per item ---
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    action = "watch_movie" if item_type == "Movie" else "watch_episode"
    existing = (await db.execute(
        select(XpLedger.id).where(
            XpLedger.user_id == user_id,
            XpLedger.action == action,
            or_(
                XpLedger.reference == item_id,
                XpLedger.reference.like(f"{item_id}:%"),
            ),
            XpLedger.created_at > cutoff,
        )
        .limit(1)
    )).scalar_one_or_none()
    if existing:
        logger.debug("[XP] cooldown active: user=%s item=%s", user_id, item_id)
        return None

    # Use a time-bucketed reference so the unique constraint allows
    # the same item after 24h: "item_id:YYYY-MM-DD"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    reference = f"{item_id}:{today}"

    return await grant_xp(db, user_id, action, reference)


async def grant_daily_login_xp(
    db: AsyncSession, user_id: int
) -> dict | None:
    """Grant daily login XP (max 1 per calendar day)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return await grant_xp(db, user_id, "daily_login", today)


async def _daily_xp_sum(
    db: AsyncSession,
    user_id: int,
    today_start: datetime,
    actions: tuple[str, ...],
) -> int:
    """Sum XP granted today for the given action types."""
    result = await db.execute(
        select(func.coalesce(func.sum(XpLedger.xp), 0)).where(
            XpLedger.user_id == user_id,
            XpLedger.action.in_(actions),
            XpLedger.created_at >= today_start,
        )
    )
    return result.scalar() or 0
