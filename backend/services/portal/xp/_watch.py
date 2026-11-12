"""
XP for watching a movie or an episode.

Anti-abuse:
  - Watch XP requires ≥85% of runtime AND item type Movie/Episode
  - Watched duration is clamped to runtime (pauses can't inflate the ratio)
  - No daily cap on watch XP (if you watch 10h, you earned it)
  - Cooldown: same item can't grant XP within 24h
"""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.xp_ledger import XpLedger
from services.portal._watch_threshold import WATCHED_THRESHOLD

from ._grants import grant_xp

logger = logging.getLogger("mediakeeper.portal.xp")

MIN_WATCH_PERCENT = WATCHED_THRESHOLD
WATCH_XP_ITEM_TYPES = {"Movie", "Episode"}  # Trailers, MusicVideo, LiveTV…
                                            # are deliberately excluded.


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
    cutoff = datetime.now(UTC) - timedelta(hours=24)
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
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    reference = f"{item_id}:{today}"

    return await grant_xp(db, user_id, action, reference)
