import os
import time
import logging
from core.http_client import get_external_client
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("mediakeeper.tmdb")

TMDB_BASE    = "https://api.themoviedb.org/3"
LANGUAGE     = os.getenv("TMDB_LANGUAGE", "fr-FR")

# In-memory key cache (avoids a DB call on every request)
_cached_key: str = ""

# Per-item runtime + year cache for the Top 20 enrichment (≤ 40 entries).
# Runtime + year are immutable post-release, so a 24h TTL is safe; a
# container restart naturally invalidates the cache on top of it.
_meta_cache: dict[tuple[int, str], tuple[dict, float]] = {}
_META_TTL_SEC = 86400  # 24h — runtime/year immutable, restart-invalidated.


def invalidate_tmdb_key_cache():
    """Invalidate the TMDB key cache (call when the admin changes the key)."""
    global _cached_key
    _cached_key = ""


async def _get_tmdb_key(db: AsyncSession | None = None) -> str:
    """Fetch the TMDB key from the DB, with an env-var fallback."""
    global _cached_key
    if _cached_key:
        return _cached_key
    # 1. From the DB
    if db:
        from services.settings import get_setting
        key = await get_setting(db, "tmdb.api_key")
        if key:
            _cached_key = key
            return key
    # 2. Fallback env var
    key = os.getenv("TMDB_API_KEY", "")
    if key:
        _cached_key = key
    return key


def _tmdb_headers_sync(api_key: str) -> dict:
    """Build the TMDB headers with a provided key."""
    if not api_key:
        raise ValueError("TMDB_API_KEY not configured. Go to Settings -> Configuration -> TMDB.")
    return {
        "Authorization": f"Bearer {api_key}",
        "accept": "application/json",
    }


async def _search_tmdb(media_type: str, query: str, db: AsyncSession | None = None, language: str | None = None, year: int | None = None) -> list | dict:
    """
    Generic TMDB search.
    media_type: "movie" or "tv"
    """
    api_key = await _get_tmdb_key(db)
    endpoint = "search/movie" if media_type == "movie" else "search/tv"
    title_key = "title" if media_type == "movie" else "name"
    date_key  = "release_date" if media_type == "movie" else "first_air_date"
    url_segment = "movie" if media_type == "movie" else "tv"
    lang = language or LANGUAGE

    params: dict[str, str | int] = {"query": query, "language": lang, "page": 1}
    if year:
        # Empty/zero values would be rejected by TMDB and silently filter out
        # every result — only include the param when it's a real filter.
        year_key = "primary_release_year" if media_type == "movie" else "first_air_date_year"
        params[year_key] = year

    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/{endpoint}",
            params=params,
            headers=_tmdb_headers_sync(api_key),
        )
        data    = res.json()
        results = data.get("results", [])

        return [{
            "id":       r.get("id"),
            "title":    r.get(title_key, ""),
            "year":     r.get(date_key, "")[:4] if r.get(date_key) else "",
            "overview": r.get("overview", ""),
            "poster":   f"https://image.tmdb.org/t/p/w200{r['poster_path']}" if r.get("poster_path") else "",
            "vote":     round(r.get("vote_average", 0), 1),
            "tmdb_url": f"https://www.themoviedb.org/{url_segment}/{r.get('id')}",
            "type":     media_type,
            "genre_ids": r.get("genre_ids", []),
        } for r in results[:8]]

    except Exception as e:
        logger.error(f"Error _search_tmdb({media_type}): {e}")
        return {"error": str(e)}


async def search_movie(query: str, db: AsyncSession | None = None, language: str | None = None, year: int | None = None):
    """Search for a movie on TMDB."""
    return await _search_tmdb("movie", query, db, language=language, year=year)


async def search_tv(query: str, db: AsyncSession | None = None, language: str | None = None, year: int | None = None):
    """Search for a series on TMDB."""
    return await _search_tmdb("tv", query, db, language=language, year=year)


async def get_tv_seasons(tmdb_id: int, db: AsyncSession | None = None, language: str | None = None):
    """Fetch the seasons of a series."""
    api_key = await _get_tmdb_key(db)
    lang = language or LANGUAGE
    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/tv/{tmdb_id}",
            params={"language": lang},
            headers=_tmdb_headers_sync(api_key),
        )
        data    = res.json()
        seasons = data.get("seasons", [])

        return [{
            "number":   s.get("season_number"),
            "name":     s.get("name", ""),
            "episodes": s.get("episode_count", 0),
        } for s in seasons if s.get("season_number", 0) > 0]

    except Exception as e:
        logger.error(f"Error get_tv_seasons: {e}")
        return {"error": str(e)}


def _is_generic_episode_name(name: str, episode_number: int) -> bool:
    """Detect TMDB placeholder names like 'Episode 1' / 'Episode 12' that
    show up when a show has no translated title for the requested
    language. These aren't useful to the user so we fall back to EN."""
    if not name:
        return True
    stripped = name.strip().lower()
    # Strip accents on common FR variants
    stripped = stripped.replace("épisode", "episode")
    suffix = str(episode_number)
    return stripped == f"episode {suffix}" or stripped == f"episode {suffix:>02}"


async def get_season_episodes(tmdb_id: int, season: int, db: AsyncSession | None = None, language: str | None = None):
    """Fetch the episodes of a season.

    When the requested language has no episode title (TMDB returns
    "Episode N"), we fall back to the English version to avoid
    showing an empty name or the placeholder in the request picker.
    """
    api_key = await _get_tmdb_key(db)
    lang = language or LANGUAGE
    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/tv/{tmdb_id}/season/{season}",
            params={"language": lang},
            headers=_tmdb_headers_sync(api_key),
        )
        data     = res.json()
        episodes = data.get("episodes", [])

        # Which episodes still need a real name?
        needs_fallback = [
            e.get("episode_number") for e in episodes
            if _is_generic_episode_name(e.get("name", ""), e.get("episode_number") or 0)
        ]
        en_by_num: dict[int, str] = {}
        if needs_fallback and not lang.startswith("en"):
            try:
                en_res = await client.get(
                    f"{TMDB_BASE}/tv/{tmdb_id}/season/{season}",
                    params={"language": "en-US"},
                    headers=_tmdb_headers_sync(api_key),
                )
                en_data = en_res.json()
                for e in en_data.get("episodes", []):
                    num = e.get("episode_number")
                    if num is None:
                        continue
                    name = (e.get("name") or "").strip()
                    if name and not _is_generic_episode_name(name, num):
                        en_by_num[num] = name
            except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
                pass  # Fallback best-effort only.

        out = []
        for e in episodes:
            num = e.get("episode_number")
            name = (e.get("name") or "").strip()
            if _is_generic_episode_name(name, num or 0) and num in en_by_num:
                name = en_by_num[num]
            out.append({"number": num, "name": name})
        return out

    except Exception as e:
        logger.error(f"Error get_season_episodes: {e}")
        return {"error": str(e)}


async def get_media_detail(media_type: str, tmdb_id: int, db: AsyncSession | None = None):
    """
    Fetch the full details of a movie or series.
    media_type: "movie" or "tv"
    """
    api_key = await _get_tmdb_key(db)
    title_key = "title" if media_type == "movie" else "name"
    date_key = "release_date" if media_type == "movie" else "first_air_date"
    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/{media_type}/{tmdb_id}",
            params={"language": LANGUAGE},
            headers=_tmdb_headers_sync(api_key),
        )
        d = res.json()
        result = {
            "id": d.get("id"),
            "title": d.get(title_key, ""),
            "year": d.get(date_key, "")[:4] if d.get(date_key) else "",
            "overview": d.get("overview", ""),
            "poster": f"https://image.tmdb.org/t/p/w300{d['poster_path']}" if d.get("poster_path") else "",
            "backdrop": f"https://image.tmdb.org/t/p/w780{d['backdrop_path']}" if d.get("backdrop_path") else "",
            "vote": round(d.get("vote_average", 0), 1),
            "genres": [g.get("name", "") for g in d.get("genres", [])],
            "type": media_type,
        }
        if media_type == "tv":
            result["seasons_count"] = d.get("number_of_seasons", 0)
            result["episodes_count"] = d.get("number_of_episodes", 0)
            result["status"] = d.get("status", "")
        else:
            result["runtime"] = d.get("runtime", 0)
        return result
    except Exception as e:
        logger.error(f"Error get_media_detail({media_type}, {tmdb_id}): {e}")
        return {"error": str(e)}


async def get_media_details(
    db: AsyncSession,
    tmdb_id: int,
    media_type: str,
) -> dict | None:
    """Fetch the TMDB-canonical metadata used by the achievements runner.

    Distinct from :func:`get_media_detail` (singular) which is the
    UI-facing detail page — this variant skips the ``language`` param
    so the response carries the neutral ``original_language`` field.

    Returns ``{"original_language": str | None}`` on success, or ``None``
    on any failure (no key, network error, unknown ``media_type``). The
    short timeout keeps a slow TMDB instance from stalling the sync.
    """
    if media_type not in ("movie", "tv"):
        return None
    api_key = await _get_tmdb_key(db)
    if not api_key:
        return None
    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/{media_type}/{tmdb_id}",
            headers=_tmdb_headers_sync(api_key),
            timeout=5.0,
        )
        if res.status_code != 200:
            logger.warning(
                f"get_media_details: HTTP {res.status_code} for {media_type}/{tmdb_id}"
            )
            return None
        data = res.json()
        return {"original_language": data.get("original_language") or None}
    except Exception as e:
        logger.warning(f"get_media_details({media_type}/{tmdb_id}) failed: {e}")
        return None


async def get_meta_cached(
    tmdb_id: int,
    media_type: str,
    db: AsyncSession | None = None,
) -> dict:
    """Return cached {"runtime": int, "year": str} for a TMDB item.

    Used by the Top 20 enrichment to backfill rows the Emby payload does
    not carry. Misses fall through to a minimal TMDB call and are cached
    in-process; failures degrade to an empty dict so the caller can
    render the row without runtime / year.
    """
    if media_type not in ("movie", "tv"):
        return {}
    key = (int(tmdb_id), media_type)
    now = time.time()
    cached = _meta_cache.get(key)
    if cached and now - cached[1] < _META_TTL_SEC:
        return cached[0]
    try:
        api_key = await _get_tmdb_key(db)
        if not api_key:
            return {}
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/{media_type}/{tmdb_id}",
            params={"language": LANGUAGE},
            headers=_tmdb_headers_sync(api_key),
            timeout=5.0,
        )
        if res.status_code != 200:
            return {}
        d = res.json()
        if media_type == "movie":
            runtime = int(d.get("runtime") or 0)
            date = d.get("release_date") or ""
        else:
            eps = d.get("episode_run_time") or []
            runtime = int(eps[0]) if eps else 0
            date = d.get("first_air_date") or ""
        meta = {"runtime": runtime, "year": date[:4] if date else ""}
        _meta_cache[key] = (meta, now)
        return meta
    except Exception as e:
        logger.warning(f"get_meta_cached({media_type}/{tmdb_id}) failed: {e}")
        return {}
