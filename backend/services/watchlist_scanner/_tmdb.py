"""TMDB access for the watchlist (series + seasons) with TTL cache."""
import logging
import time

from core.http_client import get_external_client
from services.tmdb import _get_tmdb_key

logger = logging.getLogger("mediakeeper.watchlist.scanner")

TMDB_BASE = "https://api.themoviedb.org/3"

# Cache keyed by (tmdb_id, lang) / (tmdb_id, season, lang) so the same
# series can be cached in several languages side by side.
_tmdb_series_cache: dict[tuple[int, str], tuple[float, dict]] = {}
_tmdb_season_cache: dict[tuple[int, int, str], tuple[float, dict]] = {}
_TMDB_CACHE_TTL = 6 * 3600

# The scanner fetches in the default language; consumers (e.g. the dashboard
# "upcoming" widget) re-resolve display fields per viewer locale.
DEFAULT_TMDB_LANG = "fr-FR"
TMDB_LANG_BY_LOCALE = {"fr": "fr-FR", "en": "en-US"}


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


async def _tmdb_series(db, tmdb_id, lang=DEFAULT_TMDB_LANG):
    cache_key = (tmdb_id, lang)
    cached = _get_cached_tmdb_entry(_tmdb_series_cache, cache_key)
    if cached:
        return cached
    ak = await _get_tmdb_key(db)
    if not ak:
        return None
    try:
        r = await get_external_client().get(f"{TMDB_BASE}/tv/{tmdb_id}", params={"language": lang}, headers=_h(ak), timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            _tmdb_series_cache[cache_key] = (time.time(), data)
            return data
        return None
    except Exception as e:
        logger.error("_tmdb_series(%s, %s): %s", tmdb_id, lang, e)
        return None


async def _tmdb_season(db, tmdb_id, sn, lang=DEFAULT_TMDB_LANG):
    cache_key = (tmdb_id, sn, lang)
    cached = _get_cached_tmdb_entry(_tmdb_season_cache, cache_key)
    if cached:
        return cached
    ak = await _get_tmdb_key(db)
    if not ak:
        return None
    try:
        r = await get_external_client().get(f"{TMDB_BASE}/tv/{tmdb_id}/season/{sn}", params={"language": lang}, headers=_h(ak), timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            _tmdb_season_cache[cache_key] = (time.time(), data)
            return data
        return None
    except Exception as e:
        logger.error("_tmdb_season(%s, S%s, %s): %s", tmdb_id, sn, lang, e)
        return None
