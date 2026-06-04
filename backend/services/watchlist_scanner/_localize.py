"""Localize watchlist display fields to the viewer locale (read-time).

The scan and calendar caches are built once in the default TMDB language.
When a viewer's locale differs, the display fields (series name, poster,
overview, season/episode titles) are re-resolved from the per-(id, lang)
TMDB cache, cascading to en-US for the gaps and falling back to the cached
value on any miss. The default locale serves the cache untouched (no TMDB
call), and the cached objects are never mutated — new dicts are returned.
"""
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from services.tmdb import _get_tmdb_key, _is_generic_episode_name, get_media_detail, tmdb_language

from . import _tmdb
from ._tmdb import DEFAULT_TMDB_LANG

_LOCALIZE_CONCURRENCY = 4
_POSTER_BASE = "https://image.tmdb.org/t/p/w300"


async def _episode_names(db: AsyncSession, tmdb_id: int, season: int, lang: str) -> dict[int, str]:
    """Episode titles ``{number: name}`` in ``lang``, cascading to en-US for
    the generic/empty ones (a common TMDB gap for non-English languages)."""
    sd = await _tmdb._tmdb_season(db, tmdb_id, season, lang)
    if not sd:
        return {}
    names = {e.get("episode_number"): (e.get("name") or "").strip() for e in sd.get("episodes", [])}
    gaps = [n for n, name in names.items() if _is_generic_episode_name(name, n or 0)]
    if gaps and not lang.startswith("en"):
        en = await _tmdb._tmdb_season(db, tmdb_id, season, "en-US")
        for e in (en.get("episodes", []) if en else []):
            n, name = e.get("episode_number"), (e.get("name") or "").strip()
            if n in gaps and name and not _is_generic_episode_name(name, n or 0):
                names[n] = name
    return names


async def _localize_series(db: AsyncSession, s: dict, lang: str) -> dict:
    """Return a NEW series dict with TMDB display fields in ``lang`` (cached
    values kept on any miss). Never mutates ``s``."""
    tid = s.get("tmdb_id")
    sd = await _tmdb._tmdb_series(db, tid, lang) if tid else None
    if not sd:
        return s
    season_names = {x.get("season_number"): x.get("name", "") for x in sd.get("seasons", [])}
    pp = sd.get("poster_path", "")
    seasons = []
    for sn in s.get("seasons", []):
        ep_names = await _episode_names(db, tid, sn.get("season"), lang)
        seasons.append({
            **sn,
            "name": season_names.get(sn.get("season")) or sn.get("name", ""),
            "episodes": [
                {**ep, "name": ep_names.get(ep.get("episode")) or ep.get("name", "")}
                for ep in sn.get("episodes", [])
            ],
        })
    return {
        **s,
        "name": sd.get("name") or s.get("name", ""),
        "poster": f"{_POSTER_BASE}{pp}" if pp else s.get("poster", ""),
        "overview": ((sd.get("overview") or "").strip() or s.get("overview", ""))[:400],
        "seasons": seasons,
    }


async def localize_series_list(db: AsyncSession, series: list[dict], locale: str) -> list[dict]:
    """Re-resolve every series' display fields to ``locale``. The default
    locale is served as-is (the cache already holds it) — same list, no call."""
    lang = tmdb_language(locale)
    if lang == DEFAULT_TMDB_LANG or not series:
        return series
    # Warm the TMDB key cache first so the concurrent re-resolution below makes
    # no DB call on the shared session (a cold key would race db.execute calls).
    # No key configured -> nothing to re-resolve, serve the cache as-is.
    if not await _get_tmdb_key(db):
        return series
    sem = asyncio.Semaphore(_LOCALIZE_CONCURRENCY)

    async def _one(s: dict) -> dict:
        async with sem:
            return await _localize_series(db, s, lang)

    return await asyncio.gather(*(_one(s) for s in series))


async def localize_calendar_items(db: AsyncSession, items: list[dict], locale: str) -> list[dict]:
    """Re-resolve calendar items' display fields to ``locale``. TV rows go
    through the cached series/season endpoints; movie rows re-resolve title +
    synopsis via the /movie detail endpoint (the frontend renders a localized
    "movie release" label, so no episode title applies to them)."""
    lang = tmdb_language(locale)
    if lang == DEFAULT_TMDB_LANG or not items:
        return items
    if not await _get_tmdb_key(db):  # warm the key cache; no key -> serve as-is
        return items
    sem = asyncio.Semaphore(_LOCALIZE_CONCURRENCY)

    async def _one(it: dict) -> dict:
        tid = it.get("tmdb_id")
        if not tid:
            return it
        if it.get("is_movie"):
            async with sem:
                detail = await get_media_detail("movie", tid, db, locale)
            if detail.get("error"):
                return it
            return {
                **it,
                "series_name": detail.get("title") or it.get("series_name", ""),
                "poster": detail.get("poster") or it.get("poster", ""),
                "overview": ((detail.get("overview") or "").strip() or it.get("overview", ""))[:300],
            }
        async with sem:
            sd = await _tmdb._tmdb_series(db, tid, lang)
            ep_names = await _episode_names(db, tid, it["season"], lang) if it.get("season") else {}
        if not sd:
            return it
        pp = sd.get("poster_path", "")
        return {
            **it,
            "series_name": sd.get("name") or it.get("series_name", ""),
            "poster": f"{_POSTER_BASE}{pp}" if pp else it.get("poster", ""),
            "overview": ((sd.get("overview") or "").strip() or it.get("overview", ""))[:300],
            "episode_name": ep_names.get(it.get("episode")) or it.get("episode_name", ""),
        }

    return await asyncio.gather(*(_one(it) for it in items))
