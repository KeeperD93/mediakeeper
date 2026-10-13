"""Work triggered when playback rows close: watch XP and trophy checks."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("mediakeeper.stats.collector")


async def _grant_post_session_xp(db: AsyncSession, closed_sessions: list):
    """Grant XP for completed sessions (anti-abuse checks inside grant_watch_xp).

    Two-stage gate:
    - Lazy-provision: when the Emby username has no MediaKeeper row yet
      we create one so the user is visible in the admin panel — initial
      state is ``account_active=False`` (silent shadow account).
    - XP gate: profiles with ``account_active=True`` always earn XP.
      Profiles with ``account_active=False`` only earn when the admin
      explicitly opted in via ``can_earn_xp_offline`` (migration 035) —
      useful for tracking Emby activity of someone who never logs into
      MK. Otherwise watches accumulate in ``playback_sessions`` only.
    """
    try:
        from models.portal.profile import UserProfile
        from services.portal.xp import grant_watch_xp
        from services.portal.user_import import ensure_user_for_emby_session
        from services.stats import get_exclusions

        excl_list = await get_exclusions(db)
        excluded_names = set()
        for exc in excl_list:
            if exc.get("mode") == "exact":
                excluded_names.add(exc.get("value", ""))

        for sess in closed_sessions:
            if sess.item_name and sess.item_name in excluded_names:
                continue

            user = await ensure_user_for_emby_session(
                db,
                emby_username=sess.user_name,
                emby_user_id=sess.user_id,
            )
            if not user:
                continue

            profile = (await db.execute(
                select(UserProfile).where(UserProfile.user_id == user.id)
            )).scalar_one_or_none()
            if not profile:
                continue
            # XP gate: profiles with ``account_active=True`` always earn.
            # Profiles with ``account_active=False`` only earn when the admin
            # explicitly opted in via ``can_earn_xp_offline`` — useful for
            # tracking Emby activity of someone who never logs into MK.
            if not profile.account_active and not profile.can_earn_xp_offline:
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
                db, user.id, sess.user_name, source="playback_close", silent=True,
            )
    except Exception as e:
        logger.warning("[XP] post-session XP grant error: %s", e, exc_info=True)
