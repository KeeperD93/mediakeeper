"""
Achievement system facade — public API + main `check_all_achievements` dispatcher.

The implementation is split across specialized modules to keep each file under 300 lines:

  - achievements_utils.py               — shared helpers (update_progress, user filter, aggregators)
  - achievements_seed.py                — seed definitions into DB on startup
  - achievements_profile.py             — build profile trophy payload
  - achievements_seasonal.py            — compute unlock years for seasonal secrets
  - achievements_badges.py              — pin/unpin + leaderboard
  - achievements_checks_standard.py     — tiered family checks
  - achievements_checks_progression.py  — leaderboard, level, tickets, events, etc.
  - achievements_checks_secrets_a.py    — first half of secret checks
  - achievements_checks_secrets_b.py    — second half + ultimate collector + placeholders

Consumers import from this file, not the split files, to keep the public API stable.
"""
import logging
import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement
from models.playback_stats import PlaybackSession
from services.portal.exclusions import get_exclusion_filters
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from services.portal.achievements_utils import (
    MAX_PINNED_BADGES,
    update_progress,
    _load_user_achievement_map,
    _build_playback_user_filter,
)
from services.portal.achievements_seed import seed_achievements
from services.portal.achievements_profile import get_achievements_for_profile
from services.portal.achievements_badges import pin_badge, unpin_badge, get_leaderboard
from services.portal.achievements_checks_standard import check_standard
from services.portal.achievements_checks_progression import check_progression
from services.portal.achievements_checks_secrets_a import check_secrets_a
from services.portal.achievements_checks_secrets_b import check_secrets_b
from services.portal.achievements_checks_meta import check_meta

logger = logging.getLogger("mediakeeper.portal.achievements")

__all__ = [
    "seed_achievements",
    "get_achievements_for_profile",
    "check_all_achievements",
    "safe_check_all_achievements",
    "safe_check_all_achievements_in_new_session",
    "update_progress",
    "pin_badge",
    "unpin_badge",
    "get_leaderboard",
    "MAX_PINNED_BADGES",
]

# condition_types that scan all PlaybackSession rows; load them once.
_BULK_PLAYBACK_CONDITIONS = (
    "marathon_hours", "weekend_plays", "season_binge", "library_explorer",
    "total_watch_hours", "secret_indecisive", "secret_sunday",
    "secret_bgNoise", "secret_ultramarathon", "secret_butterfly",
)


async def _safe_pass(label: str, coro) -> list[dict]:
    """Run one check pass and swallow exceptions so the others keep running."""
    try:
        return await coro
    except Exception:
        logger.exception("achievements check pass failed", extra={"pass": label})
        return []


async def check_all_achievements(
    db: AsyncSession, user_id: int, user_name: str | None = None
) -> list[dict]:
    """
    Compute current stats from PlaybackSession and update all achievements.
    Returns list of newly unlocked achievements (for notification).
    Called after watch session closes, on login, on request creation, etc.
    """
    excl_filters = await get_exclusion_filters(db)

    user_filter = await _build_playback_user_filter(db, user_id, user_name)
    if user_filter is None:
        return []

    all_achs = (await db.execute(select(Achievement))).scalars().all()
    by_type: dict[str, list[Achievement]] = {}
    for a in all_achs:
        # Skip placeholders: the DB still holds them (so legacy rows survive
        # and the catalogue stays stable) but the runner does not waste
        # a query on a check that always returns 0.
        if a.id in PLACEHOLDER_IDS:
            continue
        by_type.setdefault(a.condition_type, []).append(a)

    ua_map = await _load_user_achievement_map(db, user_id)
    unlocked_ids = {
        achievement_id
        for achievement_id, ua in ua_map.items()
        if ua.unlocked
    }

    playback_rows: list[PlaybackSession] | None = None
    if any(key in by_type for key in _BULK_PLAYBACK_CONDITIONS):
        playback_rows = (await db.execute(
            select(PlaybackSession).where(user_filter, *excl_filters)
        )).scalars().all()

    unlocks: list[dict] = []
    common_kwargs = dict(
        by_type=by_type,
        user_id=user_id,
        ua_map=ua_map,
        unlocked_ids=unlocked_ids,
        user_filter=user_filter,
        excl_filters=excl_filters,
        playback_rows=playback_rows,
    )

    unlocks.extend(await _safe_pass("standard", check_standard(db, **common_kwargs)))
    unlocks.extend(await _safe_pass("progression", check_progression(db, **common_kwargs)))
    unlocks.extend(await _safe_pass("secrets_a", check_secrets_a(db, **common_kwargs)))
    unlocks.extend(await _safe_pass(
        "secrets_b", check_secrets_b(db, all_achs=all_achs, **common_kwargs)
    ))

    # Refresh unlocked_ids so meta-achievements see freshly unlocked tiers
    # from the standard/secret passes above.
    unlocked_ids = {ach_id for ach_id, ua in ua_map.items() if ua.unlocked}
    common_kwargs["unlocked_ids"] = unlocked_ids
    unlocks.extend(await _safe_pass("meta", check_meta(db, **common_kwargs)))

    await db.commit()
    return unlocks


async def safe_check_all_achievements(
    db: AsyncSession,
    user_id: int,
    user_name: str | None,
    source: str,
    *,
    silent: bool = True,
) -> list[dict]:
    """Best-effort wrapper around ``check_all_achievements``.

    Logs a structured ``achievements run`` event with the call ``source``
    and the duration in milliseconds, regardless of outcome. Failures are
    swallowed when ``silent=True`` (the default for background triggers
    fired from request handlers) so a regression in one check pass cannot
    break the originating endpoint.

    ``source`` is a free-form label; conventional values include
    ``"login"``, ``"playback_close"``, ``"chat_message"``,
    ``"request_created"``, ``"request_status_change"``, ``"ticket_created"``,
    ``"avatar_changed"``, ``"event_created"``, ``"list_created"``,
    ``"list_privacy_changed"``, ``"list_items_added"``,
    ``"manual_check"``, ``"admin_recheck"``.
    """
    started = time.perf_counter()
    unlocks: list[dict] = []
    try:
        unlocks = await check_all_achievements(db, user_id=user_id, user_name=user_name)
    except Exception:
        logger.exception(
            "achievements run failed",
            extra={"user_id": user_id, "source": source},
        )
        if not silent:
            raise
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        logger.info(
            "achievements run",
            extra={
                "user_id": user_id,
                "source": source,
                "duration_ms": duration_ms,
                "unlocks": len(unlocks),
            },
        )
    return unlocks


async def safe_check_all_achievements_in_new_session(
    user_id: int,
    user_name: str | None,
    source: str,
) -> list[dict]:
    """Convenience wrapper for FastAPI ``BackgroundTasks``: opens a fresh
    DB session so the background work does not depend on the request-scoped
    session, which may already be closed by the time the task runs.
    Always silent (failures are logged, never raised)."""
    from core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        return await safe_check_all_achievements(
            db, user_id=user_id, user_name=user_name, source=source, silent=True,
        )
