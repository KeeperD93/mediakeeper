"""Import Jellystats libraries + build the item_id -> lib_name mapping."""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import LibraryCache

logger = logging.getLogger("mediakeeper.stats.import")


async def _import_libraries(db: AsyncSession, jf_libraries: list, report: dict, now: datetime) -> None:
    """Insert missing libraries into library_cache."""
    for lib in jf_libraries:
        lib_id = str(lib.get("Id", ""))
        if not lib_id:
            continue

        existing = await db.execute(
            select(LibraryCache).where(LibraryCache.lib_id == lib_id)
        )
        if existing.scalar_one_or_none():
            report["libraries_skipped"] += 1
            continue

        col_type = lib.get("CollectionType", "unknown")
        row = LibraryCache(
            lib_id=lib_id,
            name=lib.get("Name", ""),
            collection_type=col_type,
            total_items=int(lib.get("item_count", 0) or 0),
            count_movies=0,
            count_series=int(lib.get("item_count", 0) or 0) if col_type == "tvshows" else 0,
            count_seasons=int(lib.get("season_count", 0) or 0),
            count_episodes=int(lib.get("episode_count", 0) or 0),
            size_bytes=0,
            runtime_ticks=int(lib.get("total_play_time", 0) or 0),
            updated_at=now,
        )
        if col_type == "movies":
            row.count_movies = int(lib.get("item_count", 0) or 0)
            row.count_series = 0
        db.add(row)
        report["libraries_imported"] += 1


def _build_item_to_library(
    jf_libraries: list,
    jf_lib_items: list,
    jf_lib_episodes: list,
) -> dict:
    """
    Map Jellystats item IDs (movies/series/episodes) to the library name.
    - jf_library_items: ParentId = lib.Id (for movies and series)
    - jf_library_episodes: SeriesId -> ParentId via the series mapping
    """
    lib_id_to_name = {str(lib.get("Id", "")): lib.get("Name", "") for lib in jf_libraries}
    item_to_library: dict = {}
    series_to_library: dict = {}

    for item in jf_lib_items:
        item_id = str(item.get("Id", ""))
        parent_id = str(item.get("ParentId", ""))
        lib_name = lib_id_to_name.get(parent_id, "")
        if item_id and lib_name:
            item_to_library[item_id] = lib_name
            if item.get("Type") == "Series":
                series_to_library[item_id] = lib_name

    for ep in jf_lib_episodes:
        ep_id_raw = str(ep.get("Id", ""))
        ep_id = str(ep.get("EpisodeId", "")) or ep_id_raw
        series_id = str(ep.get("SeriesId", ""))
        lib_name = series_to_library.get(series_id, "")
        if ep_id and lib_name:
            item_to_library[ep_id] = lib_name
        if ep_id_raw and lib_name:
            item_to_library[ep_id_raw] = lib_name

    logger.info(f"Jellystats import: {len(item_to_library)} items mapped to a library")
    return item_to_library
