"""
Watchlist service — tracking, ignored list and TMDB search.
Extracted from watchlist.py for maintainability.
"""

import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from core.http_client import get_external_client
from services.settings import get_watchlist_data, set_watchlist_data
from services.tmdb import _get_tmdb_key
from services.watchlist_scanner import _h

logger = logging.getLogger("mediakeeper.watchlist.tracking")
TMDB_BASE = "https://api.themoviedb.org/3"

# IGNORED
# ============================================

async def get_ignored(db: AsyncSession) -> list[str]:
    raw = await get_watchlist_data(db, "ignored")
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []

async def add_ignored(db: AsyncSession, keys: list[str]):
    c = set(await get_ignored(db))
    c.update(keys)
    await set_watchlist_data(db, "ignored", json.dumps(list(c)))

async def remove_ignored(db: AsyncSession, keys: list[str]):
    c = set(await get_ignored(db))
    for k in keys:
        c.discard(k)
    await set_watchlist_data(db, "ignored", json.dumps(list(c)))


# ============================================
# SUIVI (TRACKED)
# ============================================

async def get_tracked(db: AsyncSession) -> list[dict]:
    raw = await get_watchlist_data(db, "tracked")
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []

async def add_tracked(db: AsyncSession, media: dict):
    current = await get_tracked(db)
    existing = {(t["tmdb_id"], t["media_type"]) for t in current}
    if (media["tmdb_id"], media["media_type"]) not in existing:
        current.append(media)
        await set_watchlist_data(db, "tracked", json.dumps(current))
    return current

async def remove_tracked(db: AsyncSession, tmdb_id: int, media_type: str):
    current = await get_tracked(db)
    current = [t for t in current if not (t["tmdb_id"] == tmdb_id and t["media_type"] == media_type)]
    await set_watchlist_data(db, "tracked", json.dumps(current))
    return current


# ============================================
# RECHERCHE TMDB
# ============================================

async def search_tmdb_multi(db: AsyncSession, query: str) -> list[dict]:
    ak = await _get_tmdb_key(db)
    if not ak or not query.strip():
        return []
    try:
        client = get_external_client()
        r = await client.get(f"{TMDB_BASE}/search/multi", params={"query": query, "language": "fr-FR", "page": 1}, headers=_h(ak), timeout=10.0)
        if r.status_code != 200:
            return []
        results = []
        for x in r.json().get("results", [])[:12]:
            mt = x.get("media_type", "")
            if mt not in ("movie", "tv"):
                continue
            im = mt == "movie"
            rd = x.get("release_date" if im else "first_air_date", "")
            pp = x.get("poster_path", "")
            item = {
                "tmdb_id": x.get("id"), "media_type": mt,
                "name": x.get("title" if im else "name", ""),
                "year": rd[:4] if rd else "", "release_date": rd,
                "overview": x.get("overview", ""),
                "poster": f"https://image.tmdb.org/t/p/w300{pp}" if pp else "",
                "vote": round(x.get("vote_average", 0), 1),
                "total_seasons": 0, "total_episodes": 0,
            }
            results.append(item)

        for item in results:
            if item["media_type"] == "tv":
                try:
                    dr = await client.get(f"{TMDB_BASE}/tv/{item['tmdb_id']}", params={"language": "fr-FR"}, headers=_h(ak), timeout=8.0)
                    if dr.status_code == 200:
                        d = dr.json()
                        item["total_seasons"] = d.get("number_of_seasons", 0)
                        item["total_episodes"] = d.get("number_of_episodes", 0)
                except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
                    pass
        return results
    except Exception as e:
        logger.error(f"search_tmdb_multi: {e}")
        return []
