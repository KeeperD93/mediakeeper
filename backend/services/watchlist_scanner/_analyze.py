"""Analyze an Emby series: build the full detail (seasons/episodes)."""
import asyncio
import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from ._emby import _get_emby_episodes
from ._tmdb import _tmdb_season, _tmdb_series

logger = logging.getLogger("mediakeeper.watchlist.scanner")

_SCAN_CONCURRENCY = 4


async def _analyze_one(db: AsyncSession, emby_item: dict) -> dict | None:
    """Analyze an Emby series -> return the full detail with every episode per season."""
    tmdb_id_str = emby_item.get("ProviderIds", {}).get("Tmdb")
    if not tmdb_id_str:
        return None
    tmdb_id = int(tmdb_id_str)
    series_id = emby_item.get("Id", "")

    td = await _tmdb_series(db, tmdb_id)
    if not td:
        return None

    emby_episodes = await _get_emby_episodes(db, series_id)
    today = date.today().isoformat()
    pp = td.get("poster_path", "")

    seasons_detail = []
    total_missing = 0
    total_upcoming = 0

    for si in td.get("seasons", []):
        sn = si.get("season_number", 0)
        if sn == 0:
            continue
        sd = await _tmdb_season(db, tmdb_id, sn)
        if not sd:
            continue

        eps = []
        season_all_present = True
        for ep in sd.get("episodes", []):
            en = ep.get("episode_number")
            air = ep.get("air_date", "")
            present = (sn, en) in emby_episodes
            if not present:
                season_all_present = False

            status = "present"
            if not present:
                if air and air > today:
                    status = "upcoming"
                    total_upcoming += 1
                else:
                    status = "missing"
                    total_missing += 1

            entry: dict = {
                "episode": en, "name": ep.get("name", ""),
                "air_date": air, "status": status,
            }
            if present:
                langs = emby_episodes.get((sn, en)) or []
                if langs:
                    entry["audio_languages"] = langs
            eps.append(entry)

        seasons_detail.append({
            "season": sn,
            "name": si.get("name", f"Saison {sn}"),
            "episode_count_tmdb": len(eps),
            "episode_count_emby": sum(1 for e in eps if e["status"] == "present"),
            "all_present": season_all_present,
            "episodes": eps,
        })

    if total_missing == 0 and total_upcoming == 0:
        return None

    return {
        "series_id": series_id, "tmdb_id": tmdb_id,
        "library_id": emby_item.get("ParentId", ""),
        # Series name from TMDB (localizable per viewer at read-time); Emby name fallback.
        "name": td.get("name") or emby_item.get("Name", ""),
        "year": (emby_item.get("PremiereDate") or "")[:4],
        "poster": f"https://image.tmdb.org/t/p/w300{pp}" if pp else "",
        "emby_poster": f"/api/emby/image/{series_id}",
        "overview": (td.get("overview") or "")[:400],
        "status": td.get("status", ""),
        "total_seasons": td.get("number_of_seasons", 0),
        "total_episodes": td.get("number_of_episodes", 0),
        "first_air_date": td.get("first_air_date", ""),
        "seasons": seasons_detail,
        "missing_count": total_missing,
        "upcoming_count": total_upcoming,
    }


async def _analyze_series_batch(
    db: AsyncSession,
    series_list: list[dict],
    progress_cb=None,
) -> list[dict]:
    """Analyze several series with bounded concurrency."""
    if not series_list:
        return []

    semaphore = asyncio.Semaphore(_SCAN_CONCURRENCY)
    total = len(series_list)
    completed = 0
    results: list[dict] = []

    async def _run_one(item: dict):
        async with semaphore:
            try:
                return item, await _analyze_one(db, item)
            except Exception as e:
                logger.error("Error analyse %s: %s", item.get("Name", "?"), e)
                return item, None

    tasks = [asyncio.create_task(_run_one(item)) for item in series_list]
    try:
        for task in asyncio.as_completed(tasks):
            item, analyzed = await task
            completed += 1
            if progress_cb:
                progress_cb(completed, total, item.get("Name", ""))
            if analyzed:
                results.append(analyzed)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()

    return results
