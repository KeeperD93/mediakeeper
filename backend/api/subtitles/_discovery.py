"""Discovery endpoints: quota, scan, suggest-path, series matrix, streams."""
import asyncio

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import AsyncSessionLocal, get_db
from models.user import User
from services.opensubtitles import (
    get_available_counts,
    get_quota,
    get_series_matrix,
    remove_stream,
    scan_missing_subtitles,
    suggest_subtitle_path,
)

from ._schemas import AvailableCountRequest, BatchRemoveStreamRequest, ScanRequest

router = APIRouter()


@router.get("/quota")
async def quota(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_quota(db)


@router.post("/scan-missing")
async def scan_missing(
    req: ScanRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    results = await scan_missing_subtitles(db, languages=req.languages, library=req.library)
    return {"items": results, "total": len(results)}


@router.get("/suggest-path")
async def suggest_path(
    file_path: str = Query(...),
    language: str = Query("fr"),
    _: User = Depends(get_current_user),
):
    return {"path": suggest_subtitle_path(file_path, language)}


@router.get("/series-matrix/{series_id}")
async def series_matrix(
    series_id: str,
    languages: str = Query(""),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    lang_list = [lang.strip() for lang in languages.split(",") if lang.strip()] if languages else None
    return await get_series_matrix(db, series_id, lang_list)


@router.post("/available-count")
async def available_count(
    req: AvailableCountRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_available_counts(db, [it.model_dump() for it in req.items])


@router.get("/search-streams")
async def search_streams(
    query: str = Query(..., min_length=1),
    stream_type: str = Query("all"),  # all, audio, subtitle
    start: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Search the library for files whose streams
    match the query by title or language (e.g. VFQ, commentary, forced)."""
    from services.opensubtitles import search_streams_in_library
    return await search_streams_in_library(db, query=query, stream_type=stream_type, start=start, limit=limit)


# ffmpeg remux is disk- and CPU-heavy; cap how many run at once so a large
# batch can't saturate the NAS.
_MAX_CONCURRENT_REMUX = 2


@router.post("/batch-remove-streams")
async def batch_remove_streams(
    req: BatchRemoveStreamRequest,
    _: User = Depends(get_current_user),
):
    """Bulk-delete embedded streams (audio/subtitle) via ffmpeg remux.

    Ops are grouped by item and the groups run concurrently (bounded by
    ``_MAX_CONCURRENT_REMUX``). Same-item ops stay serialised within their group
    — two remuxes must never touch the same file at once — and each group uses
    its own DB session since an ``AsyncSession`` can't be shared across
    concurrent coroutines.
    """
    results: dict[str, list[dict]] = {"success": [], "failed": []}
    by_item: dict[str, list[int]] = {}
    for op in req.operations:
        if not op.item_id or op.stream_index < 0:
            results["failed"].append({"item_id": op.item_id, "error": "invalid_params"})
            continue
        by_item.setdefault(op.item_id, []).append(op.stream_index)

    sem = asyncio.Semaphore(_MAX_CONCURRENT_REMUX)

    async def _process_item(item_id: str, indices: list[int]) -> list[tuple[str, dict]]:
        out: list[tuple[str, dict]] = []
        async with sem, AsyncSessionLocal() as item_db:
            for stream_index in indices:
                r = await remove_stream(item_db, item_id, stream_index)
                if r.get("success"):
                    out.append(("success", {"item_id": item_id, "stream_index": stream_index}))
                else:
                    out.append(("failed", {"item_id": item_id, "error": r.get("error", "unknown")}))
        return out

    for group in await asyncio.gather(
        *(_process_item(iid, idx) for iid, idx in by_item.items())
    ):
        for bucket, payload in group:
            results[bucket].append(payload)
    return results
