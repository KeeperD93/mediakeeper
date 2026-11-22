"""Watch XP of the titles counted as watched, paid by the collector."""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackCompletion
from models.portal.xp_ledger import XpLedger
from services.portal.exclusions import is_excluded, load_exclusion_entries
from services.portal.user_import import ensure_user_for_emby_session
from services.portal.xp import (
    WatchedTitle,
    completion_reference,
    grant_completion_xp,
    watch_xp_eligible,
)

logger = logging.getLogger("mediakeeper.stats.collector")

# A watched title whose payment was missed (error, restart) is paid within this
# window; checked at the collector's start, then at this interval, not at every
# poll: a title refused for good would be tried again every few seconds.
WATCH_XP_CATCH_UP_WINDOW = timedelta(hours=48)
WATCH_XP_CATCH_UP_SECONDS = 600


async def pay_watch_xp(db: AsyncSession, completion_ids: list[int]) -> int:
    """Pay each watched title on its own and return how many were paid.

    An Emby user seen without an account gets one, unless erased at their
    request. A failure rolls the session back and costs only its own title.
    """
    entries = await load_exclusion_entries(db)
    paid = 0
    for completion_id in completion_ids:
        try:
            done = await db.get(PlaybackCompletion, completion_id)
            if done is None or is_excluded(done.item_name, entries):
                continue
            title, emby_name, emby_id = WatchedTitle.of(done), done.user_name, done.user_id
            if not watch_xp_eligible(title):
                continue
            user = await ensure_user_for_emby_session(db, emby_username=emby_name, emby_user_id=emby_id)
            if user is not None and await grant_completion_xp(db, user.id, title):
                paid += 1
        except Exception:
            logger.exception("[XP] watch XP failed for watched title %s", completion_id)
            await db.rollback()
    return paid


async def catch_up_watch_xp(db: AsyncSession, now: datetime | None = None) -> int:
    """Pay the watched titles of the last 48 hours that have no watch XP row yet."""
    since = (now or datetime.now(UTC)) - WATCH_XP_CATCH_UP_WINDOW
    found = (await db.execute(
        select(PlaybackCompletion.id, PlaybackCompletion.item_id)
        .where(PlaybackCompletion.completed_at >= since)
        .order_by(PlaybackCompletion.completed_at, PlaybackCompletion.id)
    )).all()
    references = {done.id: completion_reference(done.item_id, done.id) for done in found}
    if not references:
        return 0
    paid_already = set((await db.execute(
        select(XpLedger.reference).where(XpLedger.reference.in_(list(references.values())))
    )).scalars())
    missed = [done_id for done_id, reference in references.items() if reference not in paid_already]
    paid = await pay_watch_xp(db, missed) if missed else 0
    if paid:
        logger.info("[XP] caught up the watch XP of %s watched title(s)", paid)
    return paid
