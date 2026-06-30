"""Emby scan to refresh the `library_cache` cache (called periodically)."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from models.playback_stats import LibraryCache
from services.settings import get_active_media_source

logger = logging.getLogger("mediakeeper.stats.aggregator")


async def refresh_library_cache(db: AsyncSession):
    """
    Called every hour from main.py.
    Emby scan to refresh the library_cache table.
    """
    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        return

    url = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    if not url or not api_key:
        return

    headers = {"X-Emby-Token": api_key}
    now = datetime.now(timezone.utc)

    try:
        client = get_internal_client()

        res = await client.get(
            f"{url}/Library/VirtualFolders",
            headers=headers, timeout=15.0
        )
        if res.status_code != 200:
            logger.warning("refresh_library_cache: unable to list libraries")
            return

        libraries = res.json()
        seen_ids = set()

        for lib in libraries:
            lib_id = lib.get("ItemId", "")
            lib_name = lib.get("Name", "")
            lib_type = lib.get("CollectionType", "unknown")
            if not lib_id:
                continue

            seen_ids.add(lib_id)

            total_items, counts = await _fetch_counts(client, url, headers, lib_id)
            lib_size_bytes, lib_runtime_ticks = await _fetch_size_and_runtime(
                client, url, headers, lib_id, lib_name
            )

            existing = await db.execute(
                select(LibraryCache).where(LibraryCache.lib_id == lib_id)
            )
            row = existing.scalar_one_or_none()
            if row:
                row.name = lib_name
                row.collection_type = lib_type
                row.total_items = total_items
                row.count_movies = counts.get("Movie", 0)
                row.count_series = counts.get("Series", 0)
                row.count_seasons = counts.get("Season", 0)
                row.count_episodes = counts.get("Episode", 0)
                row.size_bytes = lib_size_bytes
                row.runtime_ticks = lib_runtime_ticks
                row.updated_at = now
            else:
                row = LibraryCache(
                    lib_id=lib_id, name=lib_name, collection_type=lib_type,
                    total_items=total_items,
                    count_movies=counts.get("Movie", 0),
                    count_series=counts.get("Series", 0),
                    count_seasons=counts.get("Season", 0),
                    count_episodes=counts.get("Episode", 0),
                    size_bytes=lib_size_bytes,
                    runtime_ticks=lib_runtime_ticks,
                    updated_at=now,
                )
                db.add(row)

        if seen_ids:
            old = await db.execute(
                select(LibraryCache).where(LibraryCache.lib_id.notin_(seen_ids))
            )
            for row in old.scalars().all():
                await db.delete(row)

        await db.commit()
        logger.info("Library cache refreshed: %s libraries", len(seen_ids))

        # Heal playback rows still on a sub-folder/slug library name (e.g. a
        # session whose Emby payload lacked LibraryName). Idempotent — only
        # suspect rows are re-resolved, so steady state / fresh installs no-op.
        from ._repair import repair_library_names
        await repair_library_names(db)

    except Exception as e:
        logger.error("Error refresh_library_cache: %s", e)


async def _fetch_counts(client, url, headers, lib_id) -> tuple[int, dict]:
    total_items = 0
    count_res = await client.get(
        f"{url}/Items",
        params={
            "ParentId": lib_id, "Recursive": "true",
            "IncludeItemTypes": "Movie,Episode,Series,Season",
            "Limit": 0, "EnableTotalRecordCount": "true",
        },
        headers=headers, timeout=15.0
    )
    if count_res.status_code == 200:
        total_items = count_res.json().get("TotalRecordCount", 0)

    counts = {}
    for item_type in ["Movie", "Series", "Season", "Episode"]:
        type_res = await client.get(
            f"{url}/Items",
            params={
                "ParentId": lib_id, "Recursive": "true",
                "IncludeItemTypes": item_type,
                "Limit": 0, "EnableTotalRecordCount": "true",
            },
            headers=headers, timeout=10.0
        )
        if type_res.status_code == 200:
            counts[item_type] = type_res.json().get("TotalRecordCount", 0)
    return total_items, counts


async def _fetch_size_and_runtime(client, url, headers, lib_id, lib_name) -> tuple[int, int]:
    lib_size_bytes = 0
    lib_runtime_ticks = 0
    try:
        start_index = 0
        page_size = 2000
        while True:
            size_batch = await client.get(
                f"{url}/Items",
                params={
                    "ParentId": lib_id, "Recursive": "true",
                    "IncludeItemTypes": "Movie,Episode",
                    "Fields": "MediaSources,RunTimeTicks",
                    "Limit": page_size,
                    "StartIndex": start_index,
                    "EnableTotalRecordCount": "true",
                },
                headers=headers, timeout=60.0
            )
            if size_batch.status_code != 200:
                break
            data = size_batch.json()
            items = data.get("Items", [])
            for item in items:
                for src in item.get("MediaSources", []):
                    lib_size_bytes += src.get("Size", 0) or 0
                lib_runtime_ticks += item.get("RunTimeTicks", 0) or 0
            total_count = data.get("TotalRecordCount", 0)
            start_index += page_size
            if start_index >= total_count or not items:
                break
    except Exception as e:
        logger.warning("Error calcul size %s: %s", lib_name, e)
    return lib_size_bytes, lib_runtime_ticks
