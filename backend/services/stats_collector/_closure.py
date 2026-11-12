"""Work triggered when playback rows close: the account of a new Emby user and trophy checks."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("mediakeeper.stats.collector")


async def _after_rows_closed(db: AsyncSession, row_ids: list[int]) -> None:
    """Check the trophies of the players whose rows closed (watch XP is paid
    earlier, when a title counts as watched: ``_watch_xp``).

    An Emby user seen without a MediaKeeper account gets one, unless erased at
    their request; it cannot sign in until the admin activates it. Every account
    linked to Emby earns from its plays, signed in or not, until it is deactivated,
    expires or is deleted.
    """
    try:
        from models.playback_stats import PlaybackSession
        from models.portal.profile import UserProfile
        from services.portal.achievements import safe_check_all_achievements
        from services.portal.exclusions import is_excluded, load_exclusion_entries
        from services.portal.user_import import ensure_user_for_emby_session

        entries = await load_exclusion_entries(db)
        # By id: a failed trophy check rolls the session back, which expires the
        # rows still to come; ``get`` reloads them (None once deleted meanwhile).
        for row_id in row_ids:
            sess = await db.get(PlaybackSession, row_id)
            if sess is None or is_excluded(sess.item_name, entries):
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

            await safe_check_all_achievements(
                db, user.id, source="playback_close", silent=True,
            )
    except Exception as e:
        logger.warning("[STATS] follow-up of closed rows failed: %s", e, exc_info=True)
