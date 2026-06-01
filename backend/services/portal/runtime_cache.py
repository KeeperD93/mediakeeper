"""Persistent TMDB runtime resolution for portal poster cards.

TMDB list endpoints (trending/popular/discover/search) never return a
runtime — only the per-item detail endpoint does. ``resolve_runtimes``
stamps a ``runtime`` (minutes) onto normalized card dicts that lack one,
reading the ``tmdb_runtime_cache`` table and filling misses from TMDB with
bounded concurrency.

It uses its own short-lived session (never the caller's, which may be used
concurrently under ``asyncio.gather``) and degrades silently — a missing
duration must never break a list response.

Any new portal surface that returns normalized card dicts should call
``resolve_runtimes`` so the duration stays consistent across the portal.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from core.http_client import get_external_client
from models.portal.tmdb_runtime import TmdbRuntimeCache
from services.tmdb import _get_tmdb_key, _tmdb_headers_sync, TMDB_BASE

logger = logging.getLogger("mediakeeper.portal.runtime_cache")

LANGUAGE = os.getenv("TMDB_LANGUAGE", "fr-FR")
# Cap concurrent TMDB detail calls across all simultaneous list renders so a
# cold cache (fresh install / many new items) can't burst hundreds of
# upstream requests at once.
_FETCH_CONCURRENCY = 8
_sem = asyncio.Semaphore(_FETCH_CONCURRENCY)


async def resolve_runtimes(items: list[dict]) -> None:
    """In place: stamp ``runtime`` (minutes) onto card dicts missing one."""
    targets = {
        (int(it["tmdb_id"]), it["media_type"])
        for it in items
        if it.get("tmdb_id")
        and it.get("media_type") in ("movie", "tv")
        and not it.get("runtime")
    }
    if not targets:
        return
    try:
        async with AsyncSessionLocal() as db:
            runtimes = await _read_cache(db, targets)
            misses = [t for t in targets if t not in runtimes]
            if misses:
                runtimes.update(await _fetch_and_store(db, misses))
    except Exception:
        logger.exception("[runtime_cache] resolve failed (%d items)", len(items))
        return
    for it in items:
        if it.get("runtime") or not it.get("tmdb_id"):
            continue
        rt = runtimes.get((int(it["tmdb_id"]), it["media_type"]))
        if rt:
            it["runtime"] = rt


async def _read_cache(
    db: AsyncSession, targets: set[tuple[int, str]],
) -> dict[tuple[int, str], int]:
    """Batch-read cached runtimes for the requested (tmdb_id, media_type)."""
    ids = {tid for tid, _ in targets}
    rows = await db.execute(
        select(
            TmdbRuntimeCache.tmdb_id,
            TmdbRuntimeCache.media_type,
            TmdbRuntimeCache.runtime,
        ).where(TmdbRuntimeCache.tmdb_id.in_(ids))
    )
    found = {(r.tmdb_id, r.media_type): r.runtime for r in rows.all()}
    return {k: v for k, v in found.items() if k in targets}


async def _fetch_and_store(
    db: AsyncSession, misses: list[tuple[int, str]],
) -> dict[tuple[int, str], int]:
    """Fetch missing runtimes from TMDB (bounded concurrency) and persist."""
    api_key = await _get_tmdb_key(db)
    if not api_key:
        return {}
    fetched = await asyncio.gather(
        *(_fetch_one(api_key, tid, mt) for tid, mt in misses)
    )
    now = datetime.now(timezone.utc)
    out = {}
    for (tid, mt), runtime in zip(misses, fetched):
        if runtime is None:  # transient failure — retry on a later render
            continue
        out[(tid, mt)] = runtime
        try:
            async with db.begin_nested():
                db.add(TmdbRuntimeCache(
                    tmdb_id=tid, media_type=mt, runtime=runtime, fetched_at=now,
                ))
                await db.flush()
        except IntegrityError:
            pass  # a concurrent render cached the same item first
    await db.commit()
    return out


async def _fetch_one(api_key: str, tmdb_id: int, media_type: str) -> int | None:
    """One TMDB detail call → runtime minutes; ``None`` on failure so the
    caller retries later instead of caching a transient error as 0."""
    try:
        async with _sem:
            res = await get_external_client().get(
                f"{TMDB_BASE}/{media_type}/{tmdb_id}",
                params={"language": LANGUAGE},
                headers=_tmdb_headers_sync(api_key),
                timeout=5.0,
            )
        if res.status_code != 200:
            return None
        d = res.json()
        if media_type == "movie":
            return int(d.get("runtime") or 0)
        eps = d.get("episode_run_time") or []
        return int(eps[0]) if eps else 0
    except Exception:
        logger.exception("[runtime_cache] fetch %s/%s failed", media_type, tmdb_id)
        return None
