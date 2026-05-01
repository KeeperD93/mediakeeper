"""
Shared exclusion filters for Portal stats + XP.

Reuses the same exclusion list (stats.exclusions setting) as the main
Statistics module so content blacklisted from stats is also excluded
from XP grants, profile stats, leaderboards, and achievements.
"""
import json as _json

from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession
from services.settings import get_setting


async def get_exclusion_filters(db: AsyncSession) -> list:
    """
    Build SQLAlchemy WHERE filters from the stats.exclusions setting.

    Returns a list of conditions that should be added to any query on
    PlaybackSession to exclude blacklisted content (e.g., theme songs,
    intro clips, test accounts).

    Usage:
        filters = await get_exclusion_filters(db)
        query = select(PlaybackSession).where(*filters, ...)
    """
    raw = await get_setting(db, "stats.exclusions")
    if not raw:
        return []
    try:
        exclusions = _json.loads(raw)
    except Exception:
        return []

    conditions = []
    for exc in exclusions:
        mode = exc.get("mode", "exact")
        value = exc.get("value", "")
        if not value:
            continue
        if mode == "exact":
            conditions.append(PlaybackSession.item_name != value)
        elif mode == "contains":
            escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(~PlaybackSession.item_name.ilike(f"%{escaped}%"))
    return conditions
