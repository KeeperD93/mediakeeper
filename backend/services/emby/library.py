"""Emby/Jellyfin library: scan, latest additions, duplicates, series search."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from services.media_manager import format_size

from .config import _get_emby_config

logger = logging.getLogger("mediakeeper.emby")


async def refresh_library(db: AsyncSession) -> dict:
    """Start a full scan of the Emby/Jellyfin library."""
    cfg = await _get_emby_config(db)
    if not cfg:
        return {"error": "no_active_media_source"}

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}

    try:
        client = get_internal_client()
        res = await client.post(
            f"{url}/Library/Refresh",
            headers=headers,
            timeout=10.0,
        )
        if res.status_code in (200, 204):
            logger.info("[EMBY] Library scan started")
            return {"success": True, "message": "Library scan started"}
        else:
            logger.error("[EMBY] scan failed: HTTP %s", res.status_code)
            return {"error": f"emby_http_{res.status_code}"}
    except Exception:
        logger.exception("[EMBY] refresh_library failed")
        return {"error": "refresh_library_failed"}


async def get_latest_items(db: AsyncSession, limit: int = 50) -> list:
    """Fetch the latest media added on Emby."""
    cfg = await _get_emby_config(db)
    if not cfg:
        return []

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}

    try:
        client = get_internal_client()
        res = await client.get(
            f"{url}/Items",
            params={
                "SortBy": "DateCreated",
                "SortOrder": "Descending",
                "IncludeItemTypes": "Movie,Episode",
                "Recursive": "true",
                "Fields": "DateCreated,Overview,ProviderIds,PremiereDate,SeriesProviderIds",
                "Limit": limit
            },
            headers=headers,
            timeout=20.0
        )
        if res.status_code == 200:
            return res.json().get("Items", [])
        return []
    except Exception:
        logger.exception("[EMBY] get_latest_items failed")
        return []


async def fetch_item_by_id(db: AsyncSession, item_id: str) -> dict | None:
    """Re-fetch a single Emby item by Id, with the same Fields as the latest-items query.

    Used by the notification engine to pick up metadata Emby may have
    enriched after the initial detection (Overview, ProductionYear,
    ProviderIds…) and avoid sending half-empty Discord cards.
    """
    if not item_id:
        return None
    cfg = await _get_emby_config(db)
    if not cfg:
        return None

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}

    try:
        client = get_internal_client()
        res = await client.get(
            f"{url}/Items",
            params={
                "Ids": item_id,
                "Fields": "DateCreated,Overview,ProviderIds,PremiereDate,SeriesProviderIds",
            },
            headers=headers,
            timeout=10.0,
        )
        if res.status_code == 200:
            items = res.json().get("Items", [])
            return items[0] if items else None
        return None
    except Exception:
        logger.exception("[EMBY] fetch_item_by_id %s failed", item_id)
        return None


def _item_group_key(item: dict) -> str:
    """Grouping key for duplicate detection (TMDB > IMDB > heuristic)."""
    providers = item.get("ProviderIds", {})
    if item.get("Type") == "Episode":
        series_name = item.get("SeriesName") or "Unknown"
        s_num = item.get("ParentIndexNumber")
        e_num = item.get("IndexNumber")
        if "Tmdb" in providers:
            return f"ep_tmdb_{providers['Tmdb']}"
        if "Imdb" in providers:
            return f"ep_imdb_{providers['Imdb']}"
        if s_num is not None and e_num is not None:
            ep_year = item.get("ProductionYear") or (item.get("PremiereDate", "")[:4])
            return f"episode_{series_name}_{ep_year}_s{s_num}_e{e_num}"
        return f"episode_id_{item.get('Id')}"

    m_year = item.get("ProductionYear") or (item.get("PremiereDate", "")[:4])
    if "Tmdb" in providers:
        return f"tmdb_{providers['Tmdb']}"
    if "Imdb" in providers:
        return f"imdb_{providers['Imdb']}"
    return f"name_{item.get('Name')}_{m_year}"


def _collect_sources(group: list) -> dict:
    """Deduplicate a group's sources by path and enrich metadata."""
    all_sources: dict = {}
    for item in group:
        for src in item.get("MediaSources", []):
            path = src.get("Path")
            if not path or path in all_sources:
                continue

            size_bytes = src.get("Size", 0)
            video_stream = next(
                (s for s in src.get("MediaStreams", []) if s.get("Type") == "Video"),
                {},
            )
            height = video_stream.get("Height", 0)
            resolution = (
                "4K" if height >= 2100
                else "1080p" if height >= 1000
                else "720p" if height >= 700
                else "SD" if height > 0 else "N/A"
            )

            all_sources[path] = {
                "path": path,
                "name": path.replace("\\", "/").split("/")[-1],
                "resolution": resolution,
                "codec": video_stream.get("Codec", "N/A").upper(),
                "size_label": format_size(size_bytes) if size_bytes else "Unknown",
                "size_bytes": size_bytes or 0,
                "height": height,
                "bitrate": video_stream.get("BitRate", 0) or src.get("Bitrate", 0) or 0,
            }
    return all_sources


def _build_duplicate_entry(group: list, all_sources: dict) -> dict:
    main_item = group[0]
    title = main_item.get("Name") or "Unknown"

    year = main_item.get("ProductionYear")
    if not year and main_item.get("PremiereDate"):
        year = main_item.get("PremiereDate")[:4]

    if main_item.get("Type") == "Episode":
        s_num = main_item.get("ParentIndexNumber")
        e_num = main_item.get("IndexNumber")
        if s_num is not None and e_num is not None:
            title = f"{main_item.get('SeriesName', '')} - S{s_num:02d}E{e_num:02d} - {title}"
        else:
            title = f"{main_item.get('SeriesName', '')} - {title}"

    thumb_id = main_item.get("SeriesId") if main_item.get("Type") == "Episode" else main_item.get("Id")
    return {
        "id": main_item.get("Id"),
        "title": title,
        "year": str(year) if year else "",
        "poster": f"/api/emby/image/{thumb_id}" if thumb_id else "",
        "sources": list(all_sources.values()),
    }


async def get_duplicates(db: AsyncSession, progress_cb=None) -> list:
    """Detect duplicate media (movies or episodes) on Emby."""
    cfg = await _get_emby_config(db)
    if not cfg:
        return []

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}

    try:
        client = get_internal_client()
        res = await client.get(
            f"{url}/Items",
            params={
                "Recursive": "true",
                "IncludeItemTypes": "Movie,Episode",
                "Fields": "MediaSources,ProviderIds,Path,PremiereDate",
            },
            headers=headers,
            timeout=30.0
        )
        if res.status_code != 200:
            return []

        items = res.json().get("Items", [])
        total_items = len(items)
        grouped: dict[str, list] = {}

        for idx, item in enumerate(items):
            if progress_cb and idx % 100 == 0:
                progress_cb(idx, total_items, "Analyzing media...")
            key = _item_group_key(item)
            grouped.setdefault(key, []).append(item)

        duplicates = []
        total_groups = len(grouped)
        for gi, (_, group) in enumerate(grouped.items()):
            if progress_cb and gi % 200 == 0:
                progress_cb(total_items + gi, total_items + total_groups, "Detecting duplicates...")
            all_sources = _collect_sources(group)
            if len(all_sources) > 1:
                duplicates.append(_build_duplicate_entry(group, all_sources))

        return duplicates
    except Exception:
        logger.exception("Error get_duplicates")
        return []


async def search_series_id(db: AsyncSession, series_name: str) -> str | None:
    """Find the Emby ID of a series by its exact name."""
    cfg = await _get_emby_config(db)
    if not cfg or not series_name:
        return None

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}

    try:
        client = get_internal_client()
        res = await client.get(
            f"{url}/Items",
            params={
                "SearchTerm": series_name,
                "IncludeItemTypes": "Series",
                "Recursive": "true",
                "Limit": 1,
                "Fields": "PrimaryImageAspectRatio",
            },
            headers=headers, timeout=10.0,
        )
        if res.status_code == 200:
            items = res.json().get("Items", [])
            if items:
                return items[0].get("Id", "")
        return None
    except Exception:
        logger.exception("[EMBY] search_series_id failed")
        return None
