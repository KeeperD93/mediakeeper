"""Social activity feed."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.request import MediaRequest
from models.portal.achievement import UserAchievement
from models.portal.social import UserRating
from models.portal.profile import UserProfile

logger = logging.getLogger("mediakeeper.portal.activity")


async def get_activity_feed(
    db: AsyncSession, limit: int = 30
) -> list[dict]:
    """Build a mixed activity feed from recent events. Never raises."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    feed = []

    try:
        req_result = await db.execute(
            select(MediaRequest)
            .where(MediaRequest.created_at >= cutoff)
            .order_by(MediaRequest.id.desc())
            .limit(10)
        )
        for r in req_result.scalars().all():
            profile = await _get_display_name(db, r.user_id)
            feed.append({
                "type": "request",
                "subtype": r.status,
                "user_id": r.user_id,
                "display_name": profile,
                "title": r.title,
                "media_type": r.media_type,
                "tmdb_id": r.tmdb_id,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            })
    except Exception as e:
        logger.warning(f"[ACTIVITY] requests query failed: {e}")

    try:
        ach_result = await db.execute(
            select(UserAchievement)
            .where(
                UserAchievement.unlocked == True,  # noqa: E712
                UserAchievement.unlocked_at >= cutoff,
            )
            .order_by(UserAchievement.unlocked_at.desc())
            .limit(10)
        )
        for ua in ach_result.scalars().all():
            profile = await _get_display_name(db, ua.user_id)
            feed.append({
                "type": "achievement",
                "user_id": ua.user_id,
                "display_name": profile,
                "achievement_id": ua.achievement_id,
                "created_at": ua.unlocked_at.isoformat() if ua.unlocked_at else "",
            })
    except Exception as e:
        logger.warning(f"[ACTIVITY] achievements query failed: {e}")

    try:
        rating_result = await db.execute(
            select(UserRating)
            .where(UserRating.created_at >= cutoff)
            .order_by(UserRating.id.desc())
            .limit(10)
        )
        for r in rating_result.scalars().all():
            profile = await _get_display_name(db, r.user_id)
            feed.append({
                "type": "rating",
                "user_id": r.user_id,
                "display_name": profile,
                "tmdb_id": r.tmdb_id,
                "media_type": r.media_type,
                "rating": r.rating,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            })
    except Exception as e:
        logger.warning(f"[ACTIVITY] ratings query failed: {e}")

    feed.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return feed[:limit]


# Simple cache to avoid N+1
_name_cache: dict[int, str] = {}


async def _get_display_name(db: AsyncSession, user_id: int) -> str:
    if user_id in _name_cache:
        return _name_cache[user_id]
    result = await db.execute(
        select(UserProfile.display_name).where(UserProfile.user_id == user_id)
    )
    name = result.scalar_one_or_none() or f"User #{user_id}"
    _name_cache[user_id] = name
    return name
