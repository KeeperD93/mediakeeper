"""Playback/cache aggregation for the Statistics -> Libraries view."""
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import LibraryCache, PlaybackSession

from .._helpers import _apply_filters, _get_library_name_map, _normalize_library_name
from ..exclusions import _get_exclusion_filters
from ._refresh import refresh_library_cache


async def get_libraries_stats(db: AsyncSession):
    """
    Lit from le cache BDD (library_cache) + stats de playback.
    If the cache is empty, trigger a refresh.
    """
    count_res = await db.execute(select(func.count(LibraryCache.id)))
    cache_count = count_res.scalar() or 0

    if cache_count == 0:
        await refresh_library_cache(db)

    libs_res = await db.execute(select(LibraryCache).order_by(LibraryCache.name))
    libs = libs_res.scalars().all()

    exc_filters = await _get_exclusion_filters(db)
    lib_map = await _get_library_name_map(db)

    stats_by_library = await _aggregate_play_stats(db, exc_filters, lib_map)
    last_play_by_library = await _aggregate_last_play(db, exc_filters, lib_map)

    result = []
    for lib in libs:
        stats = stats_by_library.get(lib.name, {})
        last_play = last_play_by_library.get(lib.name, {})

        thumb_url = f"/api/emby/image/{lib.lib_id}" if lib.lib_id else ""

        counts = {}
        if lib.count_movies:
            counts["Movie"] = lib.count_movies
        if lib.count_series:
            counts["Series"] = lib.count_series
        if lib.count_seasons:
            counts["Season"] = lib.count_seasons
        if lib.count_episodes:
            counts["Episode"] = lib.count_episodes

        result.append({
            "name": lib.name,
            "type": lib.collection_type or "unknown",
            "item_id": lib.lib_id,
            "thumb_url": thumb_url,
            "total_items": lib.total_items,
            "counts": counts,
            "size_bytes": lib.size_bytes,
            "runtime_ticks": lib.runtime_ticks,
            "total_plays": stats.get("total_plays", 0),
            "total_duration_ticks": stats.get("total_duration_ticks", 0),
            "last_play_name": last_play.get("last_play_name"),
            "last_play_at": last_play["last_play_at"].isoformat() if last_play.get("last_play_at") else None,
            "cache_updated_at": lib.updated_at.isoformat() if lib.updated_at else None,
        })

    return result


async def _aggregate_play_stats(db, exc_filters, lib_map) -> dict[str, dict]:
    stats_rows = (
        await db.execute(
            _apply_filters(
                select(
                    PlaybackSession.library_name.label("library_name"),
                    func.count(PlaybackSession.id).label("play_count"),
                    func.sum(
                        case(
                            (PlaybackSession.position_ticks.isnot(None), PlaybackSession.position_ticks),
                            else_=0,
                        )
                    ).label("duration_ticks"),
                ).where(
                    PlaybackSession.library_name.isnot(None),
                    PlaybackSession.library_name != "",
                ).group_by(PlaybackSession.library_name),
                exc_filters,
            )
        )
    ).all()

    out: dict[str, dict] = {}
    for row in stats_rows:
        normalized_name = _normalize_library_name(row.library_name, lib_map)
        entry = out.setdefault(
            normalized_name,
            {"total_plays": 0, "total_duration_ticks": 0},
        )
        entry["total_plays"] += row.play_count or 0
        entry["total_duration_ticks"] += row.duration_ticks or 0
    return out


async def _aggregate_last_play(db, exc_filters, lib_map) -> dict[str, dict]:
    last_play_subq = _apply_filters(
        select(
            PlaybackSession.library_name.label("library_name"),
            PlaybackSession.item_name.label("item_name"),
            PlaybackSession.last_seen_at.label("last_seen_at"),
            func.row_number().over(
                partition_by=PlaybackSession.library_name,
                order_by=[PlaybackSession.last_seen_at.desc(), PlaybackSession.id.desc()],
            ).label("rn"),
        ).where(
            PlaybackSession.library_name.isnot(None),
            PlaybackSession.library_name != "",
            PlaybackSession.last_seen_at.isnot(None),
        ),
        exc_filters,
    ).subquery()

    last_play_rows = (
        await db.execute(
            select(
                last_play_subq.c.library_name,
                last_play_subq.c.item_name,
                last_play_subq.c.last_seen_at,
            ).where(last_play_subq.c.rn == 1)
        )
    ).all()

    out: dict[str, dict] = {}
    for row in last_play_rows:
        normalized_name = _normalize_library_name(row.library_name, lib_map)
        existing = out.get(normalized_name)
        if existing and existing["last_play_at"] and row.last_seen_at and existing["last_play_at"] >= row.last_seen_at:
            continue
        out[normalized_name] = {
            "last_play_name": row.item_name,
            "last_play_at": row.last_seen_at,
        }
    return out
