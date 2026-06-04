"""Re-resolve stored request titles to the viewer locale (read-time).

``MediaRequest.title`` is a snapshot frozen in the requester's language at
creation. The moderation and user request lists re-resolve it to the viewer's
locale via the TMDB detail endpoint, cached per ``(tmdb_id, media_type, lang)``.
The default locale is served as-is (no call) and the input dicts are never
mutated — new dicts are returned, mirroring the watchlist localize pattern.
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


async def _localized_title(
    db: AsyncSession, media_type: str, tmdb_id: int, lang: str, locale: str
) -> str:
    """Cached localized title for one item (empty string on TMDB failure so the
    caller keeps the stored title)."""
    key = (tmdb_id, media_type, lang)
    entry = _title_cache.get(key)
    if entry and time.time() - entry[0] < _CACHE_TTL_SEC:
        return entry[1]
    detail = await get_media_detail(media_type, tmdb_id, db, locale)
    if detail.get("error"):
        return ""
    title = detail.get("title") or ""
    _title_cache[key] = (time.time(), title)
    return title


async def localize_request_titles(
    db: AsyncSession, items: list[dict], locale: str
) -> list[dict]:
    """Re-resolve each serialized request's ``title`` to ``locale``. The default
    language is served as-is (the stored title already holds it) — same list, no
    TMDB call. Rows without a usable tmdb_id are kept untouched."""
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
            title = await _localized_title(db, mt, tid, lang, locale)
        return {**it, "title": title} if title else it

    return await asyncio.gather(*(_one(it) for it in items))
