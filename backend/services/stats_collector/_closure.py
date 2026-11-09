"""Work triggered when playback rows close: watch XP and trophy checks."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("mediakeeper.stats.collector")


async def _grant_post_session_xp(db: AsyncSession, closed_sessions: list):
    """Grant XP for completed sessions (anti-abuse checks inside grant_watch_xp).

    An Emby user seen without a MediaKeeper account gets one, unless erased at
    their request; it cannot sign in until the admin activates it. Every account
    linked to Emby earns from its plays, signed in or not, until it is deactivated,
    expires or is deleted.
    """
    try:
        from models.playback_stats import PlaybackSession
        from models.portal.profile import UserProfile
        from services.portal.user_import import ensure_user_for_emby_session
        from services.portal.xp import grant_watch_xp
        from services.stats import get_exclusions

        excl_list = await get_exclusions(db)
        excluded_names = set()
        for exc in excl_list:
            if exc.get("mode") == "exact":
                excluded_names.add(exc.get("value", ""))

        # By id: a failed trophy check rolls the session back, which expires the
        # rows still to come; ``get`` reloads them (None once deleted meanwhile).
        for sess_id in [sess.id for sess in closed_sessions]:
            sess = await db.get(PlaybackSession, sess_id)
            if sess is None or (sess.item_name and sess.item_name in excluded_names):
                continue

            user = await ensure_user_for_emby_session(
                db,
                emby_username=sess.user_name,
                emby_user_id=sess.user_id,
            )
            # Deactivating, expiring or deleting an account clears ``is_active``;
            # an account still waiting for its first activation earns.
            if not user or not user.is_active:
                continue

            profile = (await db.execute(
                select(UserProfile).where(UserProfile.user_id == user.id)
            )).scalar_one_or_none()
            if not profile:
                continue

            wall_duration = 0
            if sess.started_at and sess.ended_at:
                wall_duration = int(
                    (sess.ended_at - sess.started_at).total_seconds()
                )
            position_duration = int((sess.position_ticks or 0) / 10_000_000)
            duration = max(wall_duration, position_duration)
            await grant_watch_xp(
                db,
                user_id=user.id,
                item_id=sess.item_id or "",
                item_type=sess.item_type or "Movie",
                duration_seconds=duration,
                runtime_ticks=sess.duration_ticks,
            )

            from services.portal.achievements import safe_check_all_achievements
            await safe_check_all_achievements(
                db, user.id, source="playback_close", silent=True,
            )
    except Exception as e:
        logger.warning("[XP] post-session XP grant error: %s", e, exc_info=True)
