"""
Watchlist API routes v3 — persistent scan, results from DB.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.auth import get_current_user, require_csrf
from models.user import User
from services.tmdb import get_media_detail
from services.watchlist import (
    get_series_libraries, get_scan_results, get_scan_status,
    full_scan, incremental_scan,
    get_calendar, refresh_calendar_month, invalidate_calendar_cache,
    get_ignored, add_ignored, remove_ignored,
    get_tracked, add_tracked, remove_tracked,
    search_tmdb_multi,
)

logger = logging.getLogger("mediakeeper.api.watchlist")
router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

async def _invalidate_calendar_cache(db: AsyncSession):
    """Invalidate the in-memory calendar cache AND the DB cache."""
    invalidate_calendar_cache()
    # Delete calendar.* entries in DB to force regeneration
    from models.watchlist_scans import WatchlistScan
    from sqlalchemy import delete as sa_delete, select as sa_select
    # Force a session flush before the delete
    await db.flush()
    result = await db.execute(
        sa_select(WatchlistScan.id).where(WatchlistScan.scan_key.like("calendar.%"))
    )
    ids = [row[0] for row in result.fetchall()]
    if ids:
        await db.execute(sa_delete(WatchlistScan).where(WatchlistScan.id.in_(ids)))
        logger.info(f"[watchlist] Invalidated {len(ids)} calendar cache entries")
    else:
        logger.info("[watchlist] No calendar cache entries to invalidate")
    await db.commit()
    # Force SQLAlchemy to re-read from the DB on subsequent queries
    db.expire_all()


@router.get("/libraries")
async def list_libraries(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await get_series_libraries(db)


@router.get("/scan")
async def scan(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    """Return the latest scan results (from DB/cache). Does not relaunch a scan."""
    return await get_scan_results(db)


@router.post("/scan/refresh")
async def scan_refresh(
    db: AsyncSession = Depends(get_db),
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
):
    """Start an incremental scan (or a full one if no result exists)."""
    result = await incremental_scan(db)
    if result.get("error") == "scan_already_running":
        raise HTTPException(status_code=409, detail="scan_already_running")
    return result


@router.post("/scan/full")
async def scan_full(
    db: AsyncSession = Depends(get_db),
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
):
    """Force a full scan."""
    result = await full_scan(db)
    if result.get("error") == "scan_already_running":
        raise HTTPException(status_code=409, detail="scan_already_running")
    return result


@router.get("/scan/status")
async def scan_status(_: User = Depends(get_current_user)):
    """Cache summary (for the dashboard tile)."""
    return get_scan_status()


@router.get("/calendar")
async def calendar(
    year: int = Query(...), month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user),
):
    return await get_calendar(db, year, month)


@router.post("/calendar/refresh")
async def calendar_refresh(
    year: int = Query(...), month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
):
    """Force regeneration of a calendar month."""
    return await refresh_calendar_month(db, year, month)


# --- Ignored ---

class IgnoreRequest(BaseModel):
    keys: list[str]

@router.get("/ignored")
async def list_ignored(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return {"ignored": await get_ignored(db)}

@router.post("/ignored/add")
async def ignore_add(
    req: IgnoreRequest,
    db: AsyncSession = Depends(get_db),
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
):
    await add_ignored(db, req.keys)
    return {"success": True}

@router.post("/ignored/remove")
async def ignore_remove(
    req: IgnoreRequest,
    db: AsyncSession = Depends(get_db),
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
):
    await remove_ignored(db, req.keys)
    return {"success": True}


# --- Tracking ---

class TrackRequest(BaseModel):
    tmdb_id: int
    media_type: str
    name: str = ""
    poster: str = ""
    overview: str = ""
    release_date: str = ""
    year: str = ""
    total_seasons: int = 0
    total_episodes: int = 0

class UntrackRequest(BaseModel):
    tmdb_id: int
    media_type: str

@router.get("/tracked")
async def list_tracked(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await get_tracked(db)

@router.post("/tracked/add")
async def track_add(
    req: TrackRequest,
    db: AsyncSession = Depends(get_db),
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
):
    r = await add_tracked(db, req.model_dump())
    await _invalidate_calendar_cache(db)
    return {"success": True, "count": len(r)}

@router.post("/tracked/remove")
async def track_remove(
    req: UntrackRequest,
    db: AsyncSession = Depends(get_db),
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
):
    r = await remove_tracked(db, req.tmdb_id, req.media_type)
    await _invalidate_calendar_cache(db)
    return {"success": True, "count": len(r)}


# --- Search ---

@router.get("/search")
async def search(q: str = Query(..., min_length=2), db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await search_tmdb_multi(db, q)


# --- TMDB detail ---

@router.get("/tmdb/{media_type}/{tmdb_id}")
async def tmdb_detail(media_type: str, tmdb_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    """Full details of a movie or series from TMDB."""
    if media_type not in ("movie", "tv"):
        return {"error": "invalid_media_type"}
    return await get_media_detail(media_type, tmdb_id, db)


# --- Upcoming episodes ---

@router.get("/upcoming")
async def upcoming_episodes(
    lang: str = Query("fr"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Upcoming episodes (sorted by air_date), display fields localized to ``lang``.

    The scan cache holds language-neutral structure (which episodes are
    upcoming) plus French display fields. The series name / poster /
    episode title are re-resolved here in the viewer's language via the
    per-(id, lang) TMDB cache, so a viewer in English sees English.
    """
    from datetime import date, timedelta
    from services.watchlist_scanner import get_scan_status, _cache as scan_cache
    from services.watchlist_scanner._tmdb import (
        _tmdb_series, _tmdb_season, TMDB_LANG_BY_LOCALE, DEFAULT_TMDB_LANG,
    )
    if not get_scan_status().get("ready") or not scan_cache:
        return []

    cutoff = (date.today() - timedelta(days=2)).isoformat()
    tmdb_lang = TMDB_LANG_BY_LOCALE.get(lang, DEFAULT_TMDB_LANG)

    # 1) Collect the language-neutral upcoming structure from the scan cache.
    pending = []
    for series in scan_cache.get("series", []):
        for season in series.get("seasons", []):
            for ep in season.get("episodes", []):
                if ep.get("status") == "upcoming" and ep.get("air_date") and ep["air_date"] >= cutoff:
                    pending.append({
                        "tmdb_id": series.get("tmdb_id"),
                        "emby_poster": series.get("emby_poster", ""),
                        "season": season.get("season", 0),
                        "episode": ep.get("episode", 0),
                        "air_date": ep.get("air_date", ""),
                    })
    pending.sort(key=lambda x: x["air_date"])
    pending = pending[:30]

    # 2) Resolve name / poster / episode title in the viewer's language.
    #    Memoized per request; the per-(id, lang) TMDB cache means the
    #    default locale hits the scanner's cache and others fetch once / 6h.
    series_memo: dict[int, tuple[str, str]] = {}
    season_memo: dict[tuple[int, int], dict[int, str]] = {}
    out = []
    for it in pending:
        tid = it["tmdb_id"]
        if tid and tid not in series_memo:
            sd = await _tmdb_series(db, tid, tmdb_lang)
            pp = sd.get("poster_path", "") if sd else ""
            poster = f"https://image.tmdb.org/t/p/w300{pp}" if pp else it["emby_poster"]
            series_memo[tid] = (sd.get("name", "") if sd else "", poster)
        series_name, poster = series_memo.get(tid, ("", it["emby_poster"]))

        skey = (tid, it["season"])
        if tid and skey not in season_memo:
            sd2 = await _tmdb_season(db, tid, it["season"], tmdb_lang)
            season_memo[skey] = {
                e.get("episode_number"): e.get("name", "")
                for e in (sd2.get("episodes", []) if sd2 else [])
            }
        episode_name = season_memo.get(skey, {}).get(it["episode"], "")

        out.append({
            "series_name": series_name,
            "poster": poster,
            "tmdb_id": tid,
            "season": it["season"],
            "episode": it["episode"],
            "episode_name": episode_name,
            "air_date": it["air_date"],
        })
    return out
