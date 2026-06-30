"""Social activity feed."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.request import MediaRequest
from models.portal.achievement import UserAchievement
from models.portal.social import UserRating
from models.portal.profile import UserProfile
from services.portal._display_name import resolve_display_name

logger = logging.getLogger("mediakeeper.portal.activity")


async def get_activity_feed(
    db: AsyncSession, limit: int = 30, *, lang: str = "fr",
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
            profile = await _get_display_name(db, r.user_id, lang)
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
        logger.warning("[ACTIVITY] requests query failed: %s", e)

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
            profile = await _get_display_name(db, ua.user_id, lang)
            feed.append({
                "type": "achievement",
                "user_id": ua.user_id,
                "display_name": profile,
                "achievement_id": ua.achievement_id,
                "created_at": ua.unlocked_at.isoformat() if ua.unlocked_at else "",
            })
    except Exception as e:
        logger.warning("[ACTIVITY] achievements query failed: %s", e)

    try:
        rating_result = await db.execute(
            select(UserRating)
            .where(UserRating.created_at >= cutoff)
            .order_by(UserRating.id.desc())
            .limit(10)
        )
        for r in rating_result.scalars().all():
            profile = await _get_display_name(db, r.user_id, lang)
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
        logger.warning("[ACTIVITY] ratings query failed: %s", e)

    feed.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return feed[:limit]


# Per-(user_id, lang) cache to avoid N+1 lookups across the three feed
# queries above. Keyed by the locale too so an EN viewer never inherits
# the FR alias resolved earlier in the same process.
_name_cache: dict[tuple[int, str], str] = {}


async def _get_display_name(
    db: AsyncSession, user_id: int, lang: str = "fr"
) -> str:
    cache_key = (user_id, lang)
    if cache_key in _name_cache:
        return _name_cache[cache_key]
    row = (await db.execute(
        select(UserProfile.display_name, UserProfile.display_name_must_set)
        .where(UserProfile.user_id == user_id)
    )).first()
    if row is None:
        name = resolve_display_name(None, user_id, lang)
    else:
        display_name, must_set = row
        effective = None if must_set else display_name
        name = resolve_display_name(effective, user_id, lang)
    _name_cache[cache_key] = name
    return name
