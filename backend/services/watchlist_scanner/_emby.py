"""Emby data access for the watchlist (libraries, series, episodes)."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from services.emby import _get_emby_config

logger = logging.getLogger("mediakeeper.watchlist.scanner")


async def get_series_libraries(db: AsyncSession) -> list[dict]:
    cfg = await _get_emby_config(db)
    if not cfg:
        return []
    url, ak = cfg
    try:
        r = await get_internal_client().get(f"{url}/Library/VirtualFolders", headers={"X-Emby-Token": ak}, timeout=15.0)
        return [{"id": f.get("ItemId", ""), "name": f.get("Name", ""), "collection_type": f.get("CollectionType", "")}
                for f in r.json() if f.get("CollectionType", "") in ("tvshows", "")] if r.status_code == 200 else []
    except Exception as e:
        logger.error(f"get_series_libraries: {e}")
        return []


async def _get_all_emby_series(db: AsyncSession, library_id: str = "") -> list[dict]:
    cfg = await _get_emby_config(db)
    if not cfg:
        return []
    url, ak = cfg
    params = {"IncludeItemTypes": "Series", "Recursive": "true",
              "Fields": "ProviderIds,Overview,PremiereDate,Status,ChildCount",
              "SortBy": "SortName", "SortOrder": "Ascending"}
    if library_id:
        params["ParentId"] = library_id
    try:
        r = await get_internal_client().get(f"{url}/Items", params=params, headers={"X-Emby-Token": ak}, timeout=30.0)
        return r.json().get("Items", []) if r.status_code == 200 else []
    except Exception as e:
        logger.error(f"_get_all_emby_series: {e}")
        return []


async def _get_emby_episodes(db: AsyncSession, series_id: str) -> set[tuple[int, int]]:
    cfg = await _get_emby_config(db)
    if not cfg:
        return set()
    url, ak = cfg
    try:
        r = await get_internal_client().get(
            f"{url}/Shows/{series_id}/Episodes",
            params={"Fields": "PremiereDate,ProviderIds"},
            headers={"X-Emby-Token": ak}, timeout=20.0)
        if r.status_code != 200:
            return set()
        return {(ep.get("ParentIndexNumber"), ep.get("IndexNumber"))
                for ep in r.json().get("Items", [])
                if ep.get("ParentIndexNumber") is not None and ep.get("IndexNumber") is not None}
    except Exception as e:
        logger.error(f"_get_emby_episodes: {e}")
        return set()
