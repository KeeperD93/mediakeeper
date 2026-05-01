"""TMDB access for the watchlist (series + seasons) with TTL cache."""
import logging
import time

from core.http_client import get_external_client
from services.tmdb import _get_tmdb_key

logger = logging.getLogger("mediakeeper.watchlist.scanner")

TMDB_BASE = "https://api.themoviedb.org/3"

_tmdb_series_cache: dict[int, tuple[float, dict]] = {}
_tmdb_season_cache: dict[tuple[int, int], tuple[float, dict]] = {}
_TMDB_CACHE_TTL = 6 * 3600


def _h(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "accept": "application/json"}


def _get_cached_tmdb_entry(cache: dict, key):
    entry = cache.get(key)
    if not entry:
        return None
    cached_at, data = entry
    if time.time() - cached_at >= _TMDB_CACHE_TTL:
        cache.pop(key, None)
        return None
    return data


async def _tmdb_series(db, tmdb_id):
    cached = _get_cached_tmdb_entry(_tmdb_series_cache, tmdb_id)
    if cached:
        return cached
    ak = await _get_tmdb_key(db)
    if not ak:
        return None
    try:
        r = await get_external_client().get(f"{TMDB_BASE}/tv/{tmdb_id}", params={"language": "fr-FR"}, headers=_h(ak), timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            _tmdb_series_cache[tmdb_id] = (time.time(), data)
            return data
        return None
    except Exception as e:
        logger.error(f"_tmdb_series({tmdb_id}): {e}")
        return None


async def _tmdb_season(db, tmdb_id, sn):
    cache_key = (tmdb_id, sn)
    cached = _get_cached_tmdb_entry(_tmdb_season_cache, cache_key)
    if cached:
        return cached
    ak = await _get_tmdb_key(db)
    if not ak:
        return None
    try:
        r = await get_external_client().get(f"{TMDB_BASE}/tv/{tmdb_id}/season/{sn}", params={"language": "fr-FR"}, headers=_h(ak), timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            _tmdb_season_cache[cache_key] = (time.time(), data)
            return data
        return None
    except Exception as e:
        logger.error(f"_tmdb_season({tmdb_id},S{sn}): {e}")
        return None
