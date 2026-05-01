"""Engagement counters for the admin dashboard 'Requests — activity' card."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import UserAchievement
from models.portal.chat import ChatMessage
from models.portal.social import UserList, UserRating


ALLOWED_WINDOWS = (1, 7)


async def get_admin_engagement(db: AsyncSession, window_days: int = 1) -> dict:
    """Return per-metric counts over the last ``window_days`` days.

    Only 1 and 7 are accepted; anything else falls back to 1 so the card
    cannot be abused to run full-table scans from an arbitrary query param.
    """
    if window_days not in ALLOWED_WINDOWS:
        window_days = 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    new_lists = (await db.execute(
        select(func.count(UserList.id))
        .where(UserList.is_deleted.is_(False), UserList.created_at >= cutoff)
    )).scalar() or 0

    achievements_unlocked = (await db.execute(
        select(func.count(UserAchievement.id))
        .where(UserAchievement.unlocked.is_(True),
               UserAchievement.unlocked_at >= cutoff)
    )).scalar() or 0

    chat_messages = (await db.execute(
        select(func.count(ChatMessage.id))
        .where(ChatMessage.deleted.is_(False),
               ChatMessage.created_at >= cutoff)
    )).scalar() or 0

    reviews = (await db.execute(
        select(func.count(UserRating.id))
        .where(UserRating.review.isnot(None), UserRating.created_at >= cutoff)
    )).scalar() or 0

    return {
        "window_days": window_days,
        "new_lists": new_lists,
        "achievements_unlocked": achievements_unlocked,
        "chat_messages": chat_messages,
        "reviews": reviews,
    }
