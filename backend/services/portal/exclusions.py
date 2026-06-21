"""
Shared exclusion filters for Portal stats + XP.

Reuses the same exclusion list (stats.exclusions setting) as the main
Statistics module so content blacklisted from stats is also excluded
from XP grants, profile stats, leaderboards, and achievements.
"""
import json as _json

from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackPauseEvent, PlaybackSession
from services.settings import get_setting


async def _load_exclusion_entries(db: AsyncSession) -> list[dict]:
    """Read and parse the ``stats.exclusions`` setting.

    Centralized so both ``PlaybackSession`` and ``PlaybackPauseEvent``
    filter helpers stay byte-for-byte aligned with the same source of
    truth (item-name blacklist edited by admins on the Stats page).
    """
    raw = await get_setting(db, "stats.exclusions")
    if not raw:
        return []
    try:
        parsed = _json.loads(raw)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


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
    conditions = []
    for exc in await _load_exclusion_entries(db):
        mode = exc.get("mode", "exact")
        value = exc.get("value", "")
        if not value:
            continue
        if mode == "exact":
            conditions.append(PlaybackSession.item_name != value)
        elif mode == "contains":
            conditions.append(~PlaybackSession.item_name.icontains(value, autoescape=True))
    return conditions


async def get_pause_event_exclusion_filters(db: AsyncSession) -> list:
    """SQLAlchemy WHERE filters for ``PlaybackPauseEvent`` mirroring the
    stats blacklist applied to ``PlaybackSession``.

    Same setting, same modes (``exact`` / ``contains``); ensures a pause
    on excluded content (e.g. an intro clip) cannot count toward the
    bathroom-break trophy.
    """
    conditions = []
    for exc in await _load_exclusion_entries(db):
        mode = exc.get("mode", "exact")
        value = exc.get("value", "")
        if not value:
            continue
        if mode == "exact":
            conditions.append(PlaybackPauseEvent.item_name != value)
        elif mode == "contains":
            conditions.append(~PlaybackPauseEvent.item_name.icontains(value, autoescape=True))
    return conditions
