"""TMDB list endpoints — trending, popular, top-rated, upcoming, family,
oscars, by-provider — plus the full-details and search helpers used by
the rest of the discover layer.

All functions in this module return a list of normalized dicts (or a
single dict for `get_full_details`). Pagination is 1-indexed (TMDB caps
at page 500).
"""
import os
import logging
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_external_client
from core.ttl_cache import cached_tmdb_list
from services.tmdb import _get_tmdb_key, _tmdb_headers_sync, TMDB_BASE
from services.portal.runtime_cache import resolve_runtimes

logger = logging.getLogger("mediakeeper.portal.discover")
LANGUAGE = os.getenv("TMDB_LANGUAGE", "fr-FR")
_IMG_BASE = "https://image.tmdb.org/t/p"

# TMDB list endpoints feed the home page; they change slowly (few times
# per day at most) and are identical for every authenticated user. A
# short in-memory TTL removes the per-visit cold-path latency and
# collapses concurrent visits into a single upstream request.
_LIST_TTL_SEC = 15 * 60
# Awards rotate once per day (seeded by today's date), so a longer TTL
# is safe and avoids re-fetching 5 TMDB pages on every request.
_OSCARS_TTL_SEC = 6 * 60 * 60


@cached_tmdb_list(_LIST_TTL_SEC)
async def get_trending(
    db: AsyncSession, page: int = 1, *, language: str | None = None,
) -> list[dict]:
    return await _fetch_list(db, "/trending/all/week", page, language=language)


@cached_tmdb_list(_LIST_TTL_SEC)
async def get_popular_movies(
    db: AsyncSession, page: int = 1, *, language: str | None = None,
) -> list[dict]:
    return await _fetch_list(db, "/movie/popular", page, language=language)


@cached_tmdb_list(_LIST_TTL_SEC)
async def get_popular_tv(
    db: AsyncSession, page: int = 1, *, language: str | None = None,
) -> list[dict]:
    return await _fetch_list(db, "/tv/popular", page, language=language)


@cached_tmdb_list(_LIST_TTL_SEC)
async def get_top_rated(
    db: AsyncSession, page: int = 1, *, language: str | None = None,
) -> list[dict]:
    return await _fetch_list(db, "/movie/top_rated", page, language=language)


@cached_tmdb_list(_LIST_TTL_SEC)
async def get_top_rated_year(
    db: AsyncSession, page: int = 1, *, language: str | None = None,
) -> list[dict]:
    """Top rated movies + TV released this year, mixed."""
    import asyncio
    import datetime
    year = datetime.datetime.now(datetime.timezone.utc).year
    movies, tv = await asyncio.gather(
        _fetch_list_params(db, "/discover/movie", page, {
            "sort_by": "vote_average.desc",
            "vote_count.gte": "50",
            "primary_release_year": str(year),
        }, language=language),
        _fetch_list_params(db, "/discover/tv", page, {
            "sort_by": "vote_average.desc",
            "vote_count.gte": "30",
            "first_air_date_year": str(year),
        }, language=language),
    )
    mixed = sorted(movies + tv, key=lambda x: x.get("vote", 0), reverse=True)
    return mixed[:20]


@cached_tmdb_list(_OSCARS_TTL_SEC)
async def get_oscar_winners(
    db: AsyncSession, page: int = 1, *, language: str | None = None,
) -> list[dict]:
    """
    Films winning / nominated for major awards (Oscars, Cannes, Cesars, BAFTA,
    Golden Globes...). This category changes very rarely, so we pull each
    day a stable random sample over 24h from a pool of 5 pages.
    """
    import random
    pool: list[dict] = []
    for p in range(1, 6):
        chunk = await _fetch_list_params(db, "/discover/movie", p, {
            "sort_by": "vote_average.desc",
            "vote_count.gte": "500",
            "with_keywords": "207317",
        }, language=language)
        if not chunk:
            break
        pool.extend(chunk)
    if not pool:
        return []

    seen: set[int] = set()
    unique: list[dict] = []
    for it in pool:
        tid = it.get("tmdb_id") or it.get("id")
        if tid and tid not in seen:
            seen.add(tid)
            unique.append(it)

    seed = date.today().isoformat()
    rnd = random.Random(seed)  # noqa: S311 -- deterministic daily shuffle for discovery cards, no security purpose
    rnd.shuffle(unique)
    return unique[:20]


@cached_tmdb_list(_LIST_TTL_SEC)
async def get_family(
    db: AsyncSession, page: int = 1, *, language: str | None = None,
) -> list[dict]:
    """Family-friendly movies (genre 10751) by popularity, with a votes floor."""
    return await _fetch_list_params(db, "/discover/movie", page, {
        "sort_by": "popularity.desc",
        "with_genres": "10751",
        "vote_count.gte": "200",
    }, language=language)


@cached_tmdb_list(_LIST_TTL_SEC)
async def get_upcoming(
    db: AsyncSession, page: int = 1, *, language: str | None = None,
) -> list[dict]:
    """Upcoming movies + TV, mixed — only future releases (today → +90 days)."""
    import asyncio
    today = date.today().isoformat()
    future = (date.today() + timedelta(days=90)).isoformat()
    movies, tv = await asyncio.gather(
        _fetch_list_params(db, "/discover/movie", page, {
            "sort_by": "popularity.desc",
            "primary_release_date.gte": today,
            "primary_release_date.lte": future,
            "vote_count.gte": "0",
        }, language=language),
        _fetch_list_params(db, "/discover/tv", page, {
            "sort_by": "popularity.desc",
            "first_air_date.gte": today,
            "first_air_date.lte": future,
        }, language=language),
    )
    mixed = movies + tv
    mixed.sort(key=lambda x: x.get("vote", 0) or 0, reverse=True)
    return mixed[:20]


@cached_tmdb_list(_LIST_TTL_SEC)
async def get_by_provider(
    db: AsyncSession,
    provider_id: int,
    media_type: str = "movie",
    page: int = 1,
    *,
    language: str | None = None,
) -> list[dict]:
    """Discover by watch provider (Netflix=8, Prime=9, Disney+=337, HBO=384, Hulu=15, Apple=350)."""
    return await _fetch_list_params(db, f"/discover/{media_type}", page, {
        "sort_by": "popularity.desc",
        "with_watch_providers": str(provider_id),
        "watch_region": "FR",
    }, language=language)


async def get_media_videos(
    db: AsyncSession, media_type: str, tmdb_id: int, *, language: str | None = None,
) -> list[dict]:
    """Get YouTube trailer keys for a media."""
    api_key = await _get_tmdb_key(db)
    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/{media_type}/{tmdb_id}/videos",
            params={"language": language or LANGUAGE},
            headers=_tmdb_headers_sync(api_key),
        )
        videos = []
        for v in res.json().get("results", []):
            if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser"):
                videos.append({
                    "key": v["key"], "name": v.get("name", ""), "type": v.get("type", ""),
                })
        return videos
    except Exception as e:
        logger.error(f"[DISCOVER] Error fetching videos: {e}")
        return []


async def _fetch_list(
    db: AsyncSession, endpoint: str, page: int, *, language: str | None = None,
) -> list[dict]:
    return await _fetch_list_params(db, endpoint, page, {}, language=language)


async def _fetch_list_params(
    db: AsyncSession,
    endpoint: str,
    page: int,
    extra_params: dict,
    *,
    include_adult: bool = False,
    language: str | None = None,
) -> list[dict]:
    """
    Fetch a TMDB discover list with optional adult-content filtering.

    ``language`` overrides the portal-wide default ``LANGUAGE`` so the
    overviews and titles come back in the caller's preferred locale.
    When ``None`` (callers that don't know the user yet), falls back to
    the portal default.

    ``include_adult`` controls BOTH the TMDB query param AND the post-filter
    that drops adult items. When False (default, safe), adult content is
    excluded twice. When True, adult items pass through (used when the user
    has explicitly disabled ``hide_adult`` in their Portal profile).
    """
    api_key = await _get_tmdb_key(db)
    try:
        client = get_external_client()
        params = {
            "language": language or LANGUAGE,
            "page": page,
            "include_adult": "true" if include_adult else "false",
            **extra_params,
        }
        res = await client.get(
            f"{TMDB_BASE}{endpoint}",
            params=params,
            headers=_tmdb_headers_sync(api_key),
        )
        results = res.json().get("results", [])
        from services.portal.requests_blacklist import blacklisted_tmdb_ids
        blacklist = await blacklisted_tmdb_ids(db)
        if include_adult:
            out = [
                n for r in results[:20]
                if (n := _normalize(r)).get("poster")
                and n.get("tmdb_id") not in blacklist
            ]
        else:
            out = [
                n for r in results[:20]
                if not r.get("adult")
                and (n := _normalize(r)).get("poster")
                and n.get("tmdb_id") not in blacklist
            ]
        await resolve_runtimes(out)
        return out
    except Exception as e:
        logger.error(f"[DISCOVER] Error fetching {endpoint}: {e}")
        return []


def _normalize(r: dict) -> dict:
    from services.portal.image_cache import is_enabled, proxied_url

    media_type = r.get("media_type", "movie")
    if "title" in r:
        media_type = "movie"
    elif "name" in r and "title" not in r:
        media_type = "tv"

    title = r.get("title") or r.get("name", "")
    date_key = "release_date" if media_type == "movie" else "first_air_date"
    year = r.get(date_key, "")[:4] if r.get(date_key) else ""

    poster_raw = f"{_IMG_BASE}/w300{r['poster_path']}" if r.get("poster_path") else ""
    backdrop_raw = f"{_IMG_BASE}/w1280{r['backdrop_path']}" if r.get("backdrop_path") else ""
    # Route the TMDB CDN URLs through the local proxy when the admin
    # opts into the image cache. Done at the normalisation layer so
    # every downstream caller (search, discover, hero, etc.) inherits
    # the rewrite without changing its own contract.
    if is_enabled():
        poster_url = proxied_url(poster_raw)
        backdrop = proxied_url(backdrop_raw)
    else:
        poster_url = poster_raw
        backdrop = backdrop_raw

    return {
        "id": r.get("id"),
        "tmdb_id": r.get("id"),
        "title": title,
        "year": year,
        "overview": r.get("overview", ""),
        "poster": poster_url,
        "poster_url": poster_url,
        "backdrop": backdrop,
        "vote": round(r.get("vote_average", 0), 1),
        "popularity": r.get("popularity", 0),
        "genres": r.get("genre_ids", []),
        "media_type": media_type,
    }
