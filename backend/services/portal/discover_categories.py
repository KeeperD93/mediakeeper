"""
Generic paginated discover layer — used by category & provider pages.

`CATEGORY_FILTERS` is the single source of truth mapping UX category
keys to TMDB query parameters. Each category specifies a media_type
("movie" | "tv" | "mixed") plus optional filters (genres, language,
release date, vote thresholds…). Asymmetric movie/tv genre ids are
declared via `movie_genres` / `tv_genres`; setting `tv_genres: None`
in mixed mode skips the TV query entirely.
"""
import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_external_client
from services.tmdb import _get_tmdb_key, _tmdb_headers_sync, TMDB_BASE
from services.portal.runtime_cache import resolve_runtimes
from services.portal.adult_filter import ADULT_KEYWORDS_CSV
from services.portal.discover_lists import _normalize

logger = logging.getLogger("mediakeeper.portal.discover")
LANGUAGE = os.getenv("TMDB_LANGUAGE", "fr-FR")

# Maps a short language code to the TMDB region code used for release-date
# filtering and popularity ranking. When no explicit region is given,
# `discover_paginated` derives it from the language.
from services.portal.discover_filters import (
    LANGUAGE_TO_REGION,
    CATEGORY_FILTERS,
    VALID_SORTS,
    _resolve_placeholder,
)



async def discover_paginated(
    db: AsyncSession,
    media_type: str,
    page: int = 1,
    *,
    sort: str = "popularity",
    language: str | None = None,
    region: str | None = None,
    extra: dict | None = None,
    movie_extra: dict | None = None,
    tv_extra: dict | None = None,
    include_adult: bool = False,
) -> dict:
    """
    Generic paginated discover query.

    Args:
        media_type: "movie" | "tv" | "mixed"
        page:       1-indexed page (TMDB caps at 500)
        sort:       "popularity" | "release" | "release_asc" | "rating"
        language:   short code (e.g. "fr") used as TMDB ``language=``.
        extra:      additional TMDB filters applied to BOTH endpoints.
        movie_extra:filters applied only to /discover/movie.
        tv_extra:   filters applied only to /discover/tv. Set to ``None`` in
                    "mixed" mode to skip the TV query entirely.

    Returns: ``{"items": [...], "page": p, "has_more": bool}``
    """
    extra = dict(extra or {})

    # Sort mapping. `release` / `release_asc` differ between movies & tv.
    if sort == "release":
        sort_param = "primary_release_date.desc" if media_type == "movie" else "first_air_date.desc"
        extra.setdefault("vote_count.gte", "10")
    elif sort == "release_asc":
        sort_param = "primary_release_date.asc" if media_type == "movie" else "first_air_date.asc"
        # No vote floor for upcoming — perfectly normal for a film
        # releasing next month to have 0 votes.
    else:
        sort_param = VALID_SORTS.get(sort, "popularity.desc")
        if sort == "rating":
            extra.setdefault("vote_count.gte", "100")

    # Language: TMDB expects "fr-FR"; expand a short code if needed.
    if language:
        lang = language if "-" in language else f"{language.lower()}-{language.upper()}"
    else:
        lang = LANGUAGE

    # Region: derive from the user's language so "fr" users see content
    # popular in France. Falls back to "US" for unknown languages.
    if not region and language:
        region = LANGUAGE_TO_REGION.get(language.lower()[:2], "US")

    base_params = {"language": lang, "sort_by": sort_param, **extra}
    if region:
        base_params["region"] = region
    # Exclude pornographic keywords TMDB does not flag as ``adult`` (hentai
    # et al.) unless the viewer has disabled hide_adult.
    base_params["include_adult"] = "true" if include_adult else "false"
    if not include_adult:
        base_params["without_keywords"] = ADULT_KEYWORDS_CSV

    async def _query(mt: str, mt_extra: dict | None = None) -> tuple[list[dict], bool]:
        api_key = await _get_tmdb_key(db)
        try:
            # Rebuild sort param per-endpoint for asymmetric sorts.
            per_mt_sort = sort_param
            if sort in ("release", "release_asc"):
                base = "primary_release_date" if mt == "movie" else "first_air_date"
                direction = "asc" if sort == "release_asc" else "desc"
                per_mt_sort = f"{base}.{direction}"

            client = get_external_client()
            query_params = {
                **base_params,
                "sort_by": per_mt_sort,
                "page": page,
                **(mt_extra or {}),
            }
            res = await client.get(
                f"{TMDB_BASE}/discover/{mt}",
                params=query_params,
                headers=_tmdb_headers_sync(api_key),
            )
            if res.status_code != 200:
                logger.warning(
                    "[DISCOVER] /discover/%s HTTP %s — params=%s",
                    mt, res.status_code, query_params,
                )
                return [], False
            j = res.json()
            results = j.get("results", [])
            total_pages = j.get("total_pages", 1)
            total_results = j.get("total_results", 0)
            if include_adult:
                normed = [n for r in results if (n := _normalize({**r, "media_type": mt})).get("poster")]
            else:
                normed = [n for r in results if not r.get("adult") and (n := _normalize({**r, "media_type": mt})).get("poster")]
            await resolve_runtimes(normed)
            if "with_watch_providers" in query_params:
                logger.info(
                    "[DISCOVER] /discover/%s provider=%s region=%s "
                    "raw=%s normed=%s total_pages=%s total_results=%s",
                    mt,
                    query_params.get("with_watch_providers"),
                    query_params.get("watch_region"),
                    len(results),
                    len(normed),
                    total_pages,
                    total_results,
                )
            return normed, page < total_pages
        except Exception as e:
            logger.error("[DISCOVER] Error /discover/%s: %s", mt, e)
            return [], False

    if media_type == "movie":
        items, has_more = await _query("movie", movie_extra)
        return {"items": items, "page": page, "has_more": has_more}
    if media_type == "tv":
        items, has_more = await _query("tv", tv_extra)
        return {"items": items, "page": page, "has_more": has_more}

    # mixed: hit both endpoints in parallel, merge while preserving the
    # requested sort (each TMDB call is already sorted, so we just pick
    # the right field to interleave).
    import asyncio
    tasks = [_query("movie", movie_extra)]
    if tv_extra is not None or sort != "release_asc":
        # tv_extra == None means "skip tv" in mixed mode (horror/thriller).
        tasks.append(_query("tv", tv_extra if tv_extra is not None else {}))

    results = await asyncio.gather(*tasks, return_exceptions=False)
    movies, has_movies = results[0]
    tv, has_tv = results[1] if len(results) > 1 else ([], False)

    merged = movies + tv
    if sort == "rating":
        merged.sort(key=lambda r: (r.get("vote") or 0), reverse=True)
    elif sort == "release_asc":
        merged.sort(key=lambda r: (r.get("year") or "9999"))
    elif sort == "release":
        merged.sort(key=lambda r: (r.get("year") or "0"), reverse=True)
    else:
        merged.sort(key=lambda r: (r.get("popularity") or 0), reverse=True)

    return {"items": merged, "page": page, "has_more": has_movies or has_tv}


async def discover_category(
    db: AsyncSession, category: str, page: int = 1,
    sort: str = "popularity", language: str | None = None,
    *, include_adult: bool = False,
) -> dict:
    """
    Paginated discover for one of the UX categories defined in
    ``CATEGORY_FILTERS``: catalogue browsers, clickable Home rows,
    and the 12 "Categories by genre" entries.
    """
    cfg = CATEGORY_FILTERS.get(category)
    if not cfg:
        return {"items": [], "page": page, "has_more": False}

    # Category default_sort overrides the client sort when set.
    effective_sort = cfg.get("default_sort") or sort

    # Shared filters applied to both endpoints
    extra: dict[str, str] = {}
    if cfg.get("with_genres"):
        extra["with_genres"] = str(cfg["with_genres"])
    if cfg.get("with_original_language"):
        extra["with_original_language"] = cfg["with_original_language"]
    if cfg.get("vote_count_gte") is not None:
        extra["vote_count.gte"] = str(cfg["vote_count_gte"])
    if cfg.get("vote_average_gte") is not None:
        extra["vote_average.gte"] = str(cfg["vote_average_gte"])

    movie_extra: dict[str, str] | None = None
    tv_extra: dict[str, str] | None = None

    if cfg.get("movie_genres") is not None:
        movie_extra = movie_extra or {}
        movie_extra["with_genres"] = str(cfg["movie_genres"])
    if "tv_genres" in cfg:
        if cfg["tv_genres"] is None:
            tv_extra = None
        else:
            tv_extra = tv_extra or {}
            tv_extra["with_genres"] = str(cfg["tv_genres"])

    if cfg.get("primary_release_year") is not None:
        movie_extra = movie_extra or {}
        movie_extra["primary_release_year"] = _resolve_placeholder(str(cfg["primary_release_year"]))
    if cfg.get("first_air_date_year") is not None:
        tv_extra = tv_extra or {}
        tv_extra["first_air_date_year"] = _resolve_placeholder(str(cfg["first_air_date_year"]))
    if cfg.get("primary_release_date_gte") is not None:
        movie_extra = movie_extra or {}
        movie_extra["primary_release_date.gte"] = _resolve_placeholder(str(cfg["primary_release_date_gte"]))
    if cfg.get("first_air_date_gte") is not None:
        tv_extra = tv_extra or {}
        tv_extra["first_air_date.gte"] = _resolve_placeholder(str(cfg["first_air_date_gte"]))

    return await discover_paginated(
        db, cfg["media_type"], page,
        sort=effective_sort,
        language=language,
        extra=extra,
        movie_extra=movie_extra,
        tv_extra=tv_extra,
        include_adult=include_adult,
    )


async def discover_provider(
    db: AsyncSession, provider_id: int, page: int = 1,
    sort: str = "popularity", language: str | None = None,
    region: str = "FR", *, include_adult: bool = False,
) -> dict:
    """
    Paginated discover for a watch provider (Netflix=8, Prime=9,
    Disney+=337, Max=384, Apple=350, Paramount=531, Crunchyroll=283…).

    Returns a mixed movies + TV list — every item carries its
    ``media_type`` so the front can render a SERIES/MOVIE tag accordingly.
    """
    extra = {
        "with_watch_providers": str(provider_id),
        "watch_region": region,
    }
    return await discover_paginated(
        db, "mixed", page, sort=sort, language=language, extra=extra,
        include_adult=include_adult,
    )
