"""Full and incremental scans + background scan."""
import json
import logging
import time
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from services.settings import set_watchlist_data

from . import _state
from ._analyze import _analyze_one, _analyze_series_batch
from ._emby import _get_all_emby_series, _get_emby_episodes

logger = logging.getLogger("mediakeeper.watchlist.scanner")


def dedupe_by_tmdb(series: list[dict]) -> list[dict]:
    """Collapse entries sharing the same `tmdb_id`, keeping the best Emby copy.

    Emby may expose the same TV series several times (split versions, multiple
    libraries) — each item produces a distinct analysis with an identical
    `tmdb_id`. The frontend keys its list by `tmdb_id`, so we keep the copy
    with the lowest `missing_count` (most episodes locally available).
    """
    best: dict[int, dict] = {}
    out: list[dict] = []
    for entry in series:
        tid = entry.get("tmdb_id")
        if tid is None:
            out.append(entry)
            continue
        current = best.get(tid)
        if current is None:
            best[tid] = entry
        elif entry.get("missing_count", 0) < current.get("missing_count", 0):
            best[tid] = entry
    out.extend(best.values())
    return out


async def full_scan(db: AsyncSession, library_id: str = "", progress_cb=None) -> dict:
    """Full scan — stores the results in the DB."""
    if not await _state.try_start_scan("full"):
        return {"error": "scan_already_running", "status": _state.get_scan_status()}

    logger.info("[WATCHLIST] Full scan started...")
    try:
        series_list = await _get_all_emby_series(db, library_id)
        results = await _analyze_series_batch(db, series_list, progress_cb=progress_cb)
        results = dedupe_by_tmdb(results)
        total_m = sum(a["missing_count"] for a in results)
        total_u = sum(a["upcoming_count"] for a in results)

        results.sort(key=lambda x: x["missing_count"], reverse=True)
        data = {"series": results, "total_missing": total_m, "total_upcoming": total_u,
                "scan_time": time.time()}

        await set_watchlist_data(db, "scan_results", json.dumps(data))
        _state.set_cache(data)
        logger.info(f"[WATCHLIST] Scan complete : {len(results)} series, {total_m} missing, {total_u} upcoming")
        _state.finish_scan()
        return data
    except Exception as exc:
        _state.finish_scan(error=str(exc)[:500])
        raise


async def incremental_scan(db: AsyncSession) -> dict:
    """
    Incremental scan: compare the current Emby list with the cache.
    - New series -> full analysis
    - Removed series -> removed from cache
    - Existing series -> only update episode statuses
    """
    if not await _state.try_start_scan("incremental"):
        return {"error": "scan_already_running", "status": _state.get_scan_status()}

    try:
        old = await _state._load_from_db(db)
        if not old or not old.get("series"):
            _state.finish_scan()
            return await full_scan(db)

        logger.info("[WATCHLIST] Incremental scan...")

        emby_series = await _get_all_emby_series(db)
        emby_by_tmdb = {}
        for s in emby_series:
            tid = s.get("ProviderIds", {}).get("Tmdb")
            if tid:
                emby_by_tmdb[int(tid)] = s

        old_by_tmdb = {s["tmdb_id"]: s for s in old["series"]}

        new_ids = set(emby_by_tmdb.keys()) - set(old_by_tmdb.keys())
        removed_ids = set(old_by_tmdb.keys()) - set(emby_by_tmdb.keys())

        updated_series = []
        today = date.today().isoformat()

        for tid, cached in old_by_tmdb.items():
            if tid in removed_ids:
                continue

            emby_item = emby_by_tmdb.get(tid)
            if not emby_item:
                updated_series.append(cached)
                continue

            series_id = emby_item.get("Id", "")
            emby_set = await _get_emby_episodes(db, series_id)
            m_count, u_count = 0, 0

            for season in cached.get("seasons", []):
                all_present = True
                for ep in season.get("episodes", []):
                    sn, en = season["season"], ep["episode"]
                    present = (sn, en) in emby_set
                    air = ep.get("air_date", "")

                    if present:
                        ep["status"] = "present"
                    elif air and air > today:
                        ep["status"] = "upcoming"
                        u_count += 1
                        all_present = False
                    else:
                        ep["status"] = "missing"
                        m_count += 1
                        all_present = False

                season["all_present"] = all_present
                season["episode_count_emby"] = sum(1 for e in season["episodes"] if e["status"] == "present")

            cached["missing_count"] = m_count
            cached["upcoming_count"] = u_count
            cached["series_id"] = series_id
            cached["emby_poster"] = f"/api/emby/image/{series_id}"
            cached["library_id"] = emby_item.get("ParentId", cached.get("library_id", ""))

            if m_count > 0 or u_count > 0:
                updated_series.append(cached)

        # Analyze new series
        for tid in new_ids:
            try:
                a = await _analyze_one(db, emby_by_tmdb[tid])
                if a:
                    updated_series.append(a)
            except Exception as e:
                logger.error(f"Error analyzing new series TMDB#{tid}: {e}")

        updated_series = dedupe_by_tmdb(updated_series)
        updated_series.sort(key=lambda x: x["missing_count"], reverse=True)
        total_m = sum(s["missing_count"] for s in updated_series)
        total_u = sum(s["upcoming_count"] for s in updated_series)

        data = {"series": updated_series, "total_missing": total_m, "total_upcoming": total_u,
                "scan_time": time.time()}

        await set_watchlist_data(db, "scan_results", json.dumps(data))
        _state.set_cache(data)

        logger.info(f"[WATCHLIST] Incremental: +{len(new_ids)} new, -{len(removed_ids)} removed, {total_m} missing")
        _state.finish_scan()
        return data
    except Exception as exc:
        _state.finish_scan(error=str(exc)[:500])
        raise


async def run_background_scan():
    if not _state.engine_ref[0]:
        return
    try:
        async with AsyncSession(_state.engine_ref[0]) as db:
            existing = await _state._load_from_db(db)
            if existing and existing.get("series"):
                await incremental_scan(db)
            else:
                await full_scan(db)
    except Exception as e:
        logger.error(f"[WATCHLIST] Error scan background: {e}")
