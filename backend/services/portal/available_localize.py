"""Re-resolve Emby-sourced list items' title + synopsis to the viewer locale.

Items from :mod:`services.portal.available` carry Emby's Name/Overview in the
library's language. When the viewer's locale maps to a non-default TMDB
language, this re-resolves title + overview per item via the TMDB detail
endpoint (its own EN cascade fills blank overviews), cached per
``(tmdb_id, media_type, lang)`` so a multi-carousel home page makes at most one
TMDB call per distinct item/language. The default locale is served untouched
(no call) and the input dicts are never mutated — new dicts are returned,
mirroring the watchlist localize pattern.
"""
import asyncio
import time

from sqlalchemy.ext.asyncio import AsyncSession

from services.tmdb import LANGUAGE, _get_tmdb_key, get_media_detail, tmdb_language

_LOCALIZE_CONCURRENCY = 4
# title/overview are effectively immutable for a released title; 6h mirrors the
# watchlist TMDB cache TTL and a container restart invalidates it on top.
_CACHE_TTL_SEC = 6 * 3600
_meta_cache: dict[tuple[int, str, str], tuple[float, dict]] = {}


async def _localized_meta(
    db: AsyncSession, media_type: str, tmdb_id: int, lang: str, locale: str
) -> dict | None:
    """Cached ``{"title", "overview"}`` for one item in ``lang`` — None on TMDB
    failure so the caller keeps the source values."""
    key = (tmdb_id, media_type, lang)
    entry = _meta_cache.get(key)
    if entry and time.time() - entry[0] < _CACHE_TTL_SEC:
        return entry[1]
    # No lock on the miss path on purpose: two concurrent misses on the same key
    # only do a redundant, idempotent TMDB fetch. A shared lock would serialise
    # the surrounding asyncio.gather (killing its bounded concurrency); a per-key
    # lock dict would leak locks unbounded. The rare duplicate call is the cheaper
    # trade-off — and errors are deliberately never cached.
    detail = await get_media_detail(media_type, tmdb_id, db, locale)
    if detail.get("error"):
        return None
    meta = {"title": detail.get("title") or "", "overview": detail.get("overview") or ""}
    _meta_cache[key] = (time.time(), meta)
    return meta


async def localize_emby_items(
    db: AsyncSession, items: list[dict], locale: str
) -> list[dict]:
    """Re-resolve each item's title + synopsis to ``locale``. The default
    language is served as-is (the Emby payload already holds it) — same list,
    no TMDB call."""
    lang = tmdb_language(locale)
    if lang == LANGUAGE or not items:
        return items
    # Warm the key cache first so the concurrent re-resolution makes no DB call
    # on the shared session; no key configured -> nothing to re-resolve.
    if not await _get_tmdb_key(db):
        return items
    sem = asyncio.Semaphore(_LOCALIZE_CONCURRENCY)

    async def _one(it: dict) -> dict:
        tid, mt = it.get("tmdb_id"), it.get("media_type")
        if not tid or mt not in ("movie", "tv"):
            return it
        async with sem:
            meta = await _localized_meta(db, mt, tid, lang, locale)
        if not meta:
            return it
        return {
            **it,
            "title": meta["title"] or it.get("title", ""),
            "overview": meta["overview"] or it.get("overview", ""),
        }

    return await asyncio.gather(*(_one(it) for it in items))
