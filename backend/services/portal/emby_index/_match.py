"""TMDB matching helpers : IMDB lookup + fuzzy title/year search."""
import logging
import re

from core.http_client import get_external_client
from services.tmdb import TMDB_BASE, _tmdb_headers_sync

logger = logging.getLogger("mediakeeper.portal.emby_index")


def _coerce_int(value) -> int | None:
    try:
        return int(value) if value else None
    except (ValueError, TypeError):
        return None


def _normalise_title(title: str) -> str:
    """Lowercase + strip punctuation + collapse whitespace for fuzzy compare."""
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title, flags=re.UNICODE)
    title = re.sub(r"\s+", " ", title).strip()
    return title


async def _resolve_by_imdb(tmdb_key: str, imdb_id: str, media_type: str) -> int | None:
    """
    Resolve an IMDB id to a TMDB id via TMDB's ``/find`` endpoint.
    Returns None when the id is malformed or TMDB doesn't know it.
    """
    if not imdb_id.startswith("tt"):
        return None
    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/find/{imdb_id}",
            params={"external_source": "imdb_id"},
            headers=_tmdb_headers_sync(tmdb_key),
        )
        if res.status_code != 200:
            return None
        data = res.json() or {}
        key = "movie_results" if media_type == "movie" else "tv_results"
        results = data.get(key) or []
        if not results:
            return None
        return _coerce_int(results[0].get("id"))
    except Exception as e:
        logger.debug("[EMBY_INDEX] IMDB lookup failed for %s: %s", imdb_id, e)
        return None


async def _resolve_by_search(
    tmdb_key: str, media_type: str, title: str, year: int | None
) -> int | None:
    """
    Last-resort TMDB search. We only accept the first hit if its title
    matches after normalisation AND its year is within ±1 (accounts for
    region-specific release offsets). Anything looser risks false
    positives and is not worth the trouble.
    """
    try:
        client = get_external_client()
        params = {"query": title}
        if year:
            if media_type == "movie":
                params["year"] = str(year)
            else:
                params["first_air_date_year"] = str(year)
        endpoint = "/search/movie" if media_type == "movie" else "/search/tv"
        res = await client.get(
            f"{TMDB_BASE}{endpoint}",
            params=params,
            headers=_tmdb_headers_sync(tmdb_key),
        )
        if res.status_code != 200:
            return None
        results = (res.json() or {}).get("results") or []
        if not results:
            return None

        norm_target = _normalise_title(title)
        for candidate in results[:5]:
            cand_title = candidate.get("title") or candidate.get("name") or ""
            orig_title = candidate.get("original_title") or candidate.get("original_name") or ""
            cand_date = candidate.get("release_date") or candidate.get("first_air_date") or ""
            cand_year = int(cand_date[:4]) if cand_date[:4].isdigit() else None

            title_ok = (
                _normalise_title(cand_title) == norm_target
                or _normalise_title(orig_title) == norm_target
            )
            year_ok = (not year) or (cand_year and abs(cand_year - year) <= 1)

            if title_ok and year_ok:
                return _coerce_int(candidate.get("id"))
        return None
    except Exception as e:
        logger.debug("[EMBY_INDEX] search lookup failed for '%s': %s", title, e)
        return None
