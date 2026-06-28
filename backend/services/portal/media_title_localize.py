"""Re-resolve stored media titles to the viewer locale (read-time).

Request / list / history titles are snapshots frozen in the author's language
at creation. Any serialized surface carrying a ``tmdb_id`` + ``media_type``
re-resolves its ``title`` to the viewer's locale via the TMDB detail endpoint,
cached per ``(tmdb_id, media_type, lang)``. The default locale is served as-is
(no call) and the input dicts are never mutated — new dicts are returned,
mirroring the watchlist localize pattern.
"""
import asyncio
import time

from sqlalchemy.ext.asyncio import AsyncSession

from services.tmdb import LANGUAGE, _get_tmdb_key, get_media_detail, tmdb_language

_LOCALIZE_CONCURRENCY = 4
# Titles are effectively immutable for a released item; 6h mirrors the
# watchlist TMDB cache TTL and a container restart invalidates it on top.
_CACHE_TTL_SEC = 6 * 3600
_title_cache: dict[tuple[int, str, str], tuple[float, str]] = {}

# Map a surface's media_type onto the two TMDB detail types. Surfaces use
# "movie"/"tv" (requests, lists) or "series" for tv (tickets); anything else
# (season/episode/other) has no localizable TMDB title.
_TMDB_TYPE = {"movie": "movie", "tv": "tv", "series": "tv"}


async def _localized_title(
    db: AsyncSession, media_type: str, tmdb_id: int, lang: str, locale: str
) -> str:
    """Cached localized title for one item (empty string on TMDB failure so the
    caller keeps the stored title)."""
    key = (tmdb_id, media_type, lang)
    entry = _title_cache.get(key)
    if entry and time.time() - entry[0] < _CACHE_TTL_SEC:
        return entry[1]
    # No lock on the miss path on purpose (see available_localize._localized_meta):
    # a rare concurrent miss does a redundant idempotent TMDB fetch, cheaper than
    # serialising the gather or leaking per-key locks. Errors are never cached.
    detail = await get_media_detail(media_type, tmdb_id, db, locale)
    if detail.get("error"):
        return ""
    title = detail.get("title") or ""
    _title_cache[key] = (time.time(), title)
    return title


async def localize_titles(
    db: AsyncSession, items: list[dict], locale: str, *, title_key: str = "title"
) -> list[dict]:
    """Re-resolve each item dict's title to ``locale``. The default language is
    served as-is (the stored title already holds it) — same list, no TMDB call.
    Items without a usable tmdb_id / media_type are kept untouched. ``title_key``
    is the dict field to localize (e.g. ``media_title`` for tickets)."""
    lang = tmdb_language(locale)
    if lang == LANGUAGE or not items:
        return items
    # No TMDB key configured -> nothing to re-resolve; serve the stored titles.
    if not await _get_tmdb_key(db):
        return items
    sem = asyncio.Semaphore(_LOCALIZE_CONCURRENCY)

    async def _one(it: dict) -> dict:
        tid = it.get("tmdb_id")
        mt = _TMDB_TYPE.get(it.get("media_type"))
        if not tid or not mt:
            return it
        async with sem:
            title = await _localized_title(db, mt, tid, lang, locale)
        return {**it, title_key: title} if title else it

    return await asyncio.gather(*(_one(it) for it in items))
