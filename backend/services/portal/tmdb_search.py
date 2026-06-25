"""TMDB live search with short-lived TTL cache + cross-ref ``available_on_emby``.

Replaces the legacy ``search_index`` flow: instead of maintaining a
local indexed copy of TMDB documents (which kept drifting out of sync
with TMDB and hosting empty ``poster_url`` rows that needed a
scheduled enrichment task to backfill), we proxy each query straight
to TMDB and absorb repeated requests from the same browsing session
with an in-memory cache.

Cache behaviour:

- Stores raw TMDB results keyed by ``(query, page, available_only,
  language)``. The Emby ``available_on_emby`` flag is stamped *after*
  the cache lookup so admin toggles take effect immediately without
  waiting for the TTL to elapse.
- TTL kept short (5 min) to balance freshness vs. call
  count.
- Hits / misses / size are exposed via :func:`get_cache_stats` so the
  admin panel can render them.
- Singleton module-level cache — the worker process and the web
  process each have their own instance, which is fine for our usage
  pattern (one user, low concurrency).
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

from cachetools import TTLCache
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.portal.discover_details import search_tmdb_multi

logger = logging.getLogger("mediakeeper.portal.tmdb_search")

# Cache configuration. Sized for a typical single-user browsing
# session (20-100 unique queries between TTL windows). The TTL is
# kept short so the cache strikes the same
# trade-off between freshness and upstream call volume.
_CACHE_MAX_SIZE = 256
_CACHE_TTL_SECONDS = 300  # 5 minutes

_CACHE_NAME = "The Movie Database API"

_cache: TTLCache = TTLCache(maxsize=_CACHE_MAX_SIZE, ttl=_CACHE_TTL_SECONDS)
_cache_lock = asyncio.Lock()
_stats: dict[str, int] = {"hits": 0, "misses": 0}


def _cache_key(
    query: str, page: int, available_only: bool, language: str | None
) -> tuple:
    return (
        (query or "").strip().lower(),
        int(page),
        bool(available_only),
        (language or "").lower(),
    )


async def search_with_cache(
    db: AsyncSession,
    query: str,
    page: int = 1,
    *,
    available_only: bool = False,
    language: str | None = None,
) -> list[dict]:
    """Live TMDB multi-search with TTL cache and Emby cross-reference.

    The cached layer holds the raw TMDB output keyed on the query
    inputs. The Emby flag is recomputed on every call so admin
    enable/disable toggles propagate without TTL latency.
    """
    key = _cache_key(query, page, available_only, language)

    async with _cache_lock:
        cached_items = _cache.get(key)
        if cached_items is not None:
            _stats["hits"] += 1
        else:
            _stats["misses"] += 1

    if cached_items is None:
        items = await search_tmdb_multi(
            db, query, page, available_only=available_only, language=language,
        )
        async with _cache_lock:
            _cache[key] = items
    else:
        items = cached_items

    return await _stamp_available_on_emby(db, items)


async def _stamp_available_on_emby(
    db: AsyncSession, items: list[dict]
) -> list[dict]:
    """Decorate each item with a fresh ``available_on_emby`` flag.

    Done outside the cached layer so an admin who toggles a user's
    access (or who imports a new title into Emby) sees the change
    reflected on the very next search, regardless of the cache TTL.
    """
    if not items:
        return items
    pairs = {
        (int(i["tmdb_id"]), i["media_type"])
        for i in items
        if i.get("tmdb_id") and i.get("media_type")
    }
    if not pairs:
        return items
    rows = (
        await db.execute(
            select(EmbyTmdbIndex.tmdb_id, EmbyTmdbIndex.media_type).where(
                tuple_(EmbyTmdbIndex.tmdb_id, EmbyTmdbIndex.media_type).in_(
                    list(pairs)
                )
            )
        )
    ).all()
    available = {(int(r[0]), r[1]) for r in rows}
    out: list[dict] = []
    for it in items:
        tmdb_id = it.get("tmdb_id")
        if tmdb_id is None:
            out.append(it)
            continue
        flagged = {
            **it,
            "available_on_emby": (int(tmdb_id), it["media_type"]) in available,
        }
        out.append(flagged)
    return out


def get_cache_stats() -> dict[str, Any]:
    """Snapshot of the cache state for the admin panel.

    Returns the cache readout: cache name, hits, misses, key
    count + a rough byte-size estimate of the cached values.
    """
    total_keys = len(_cache)
    try:
        total_value_bytes = sum(
            sys.getsizeof(json.dumps(v, default=str)) for v in _cache.values()
        )
    except Exception:  # noqa: BLE001 -- best-effort, stat readout only
        total_value_bytes = 0
    return {
        "name": _CACHE_NAME,
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "keys": total_keys,
        "max_keys": _CACHE_MAX_SIZE,
        "ttl_seconds": _CACHE_TTL_SECONDS,
        "value_bytes": total_value_bytes,
    }


def clear_cache() -> int:
    """Drop all cached entries + reset counters. Returns the count cleared."""
    n = len(_cache)
    _cache.clear()
    _stats["hits"] = 0
    _stats["misses"] = 0
    return n
