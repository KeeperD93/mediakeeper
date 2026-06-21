"""Exclusions — blacklist of content excluded from stats."""
import json as _json

from sqlalchemy.ext.asyncio import AsyncSession

from services.settings import get_setting, set_setting
from models.playback_stats import PlaybackSession


async def _get_exclusion_filters(db: AsyncSession):
    """
    Return a list of SQLAlchemy conditions to apply
    to exclude blacklisted content from stats.
    """
    raw = await get_setting(db, "stats.exclusions")
    if not raw:
        return []

    try:
        exclusions = _json.loads(raw)
    except Exception:
        return []

    filters = []
    for exc in exclusions:
        mode = exc.get("mode", "exact")
        value = exc.get("value", "")
        if not value:
            continue
        if mode == "exact":
            filters.append(PlaybackSession.item_name != value)
        elif mode == "contains":
            filters.append(~PlaybackSession.item_name.icontains(value, autoescape=True))
    return filters


async def get_exclusions(db: AsyncSession) -> list:
    """Return the configured exclusion list."""
    raw = await get_setting(db, "stats.exclusions")
    if not raw:
        return []
    try:
        return _json.loads(raw)
    except Exception:
        return []


async def add_exclusion(db: AsyncSession, mode: str, value: str) -> list:
    """Ajoute une exclusion (mode: 'exact' ou 'contains')."""
    exclusions = await get_exclusions(db)
    for exc in exclusions:
        if exc.get("mode") == mode and exc.get("value") == value:
            return exclusions
    exclusions.append({"mode": mode, "value": value})
    await set_setting(db, "stats.exclusions", _json.dumps(exclusions))
    return exclusions


async def remove_exclusion(db: AsyncSession, index: int) -> list:
    """Supprime une exclusion par index."""
    exclusions = await get_exclusions(db)
    if 0 <= index < len(exclusions):
        exclusions.pop(index)
        await set_setting(db, "stats.exclusions", _json.dumps(exclusions))
    return exclusions
