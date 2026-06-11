"""Discovery endpoints: quota, scan, suggest-path, series matrix, streams."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
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


@router.post("/batch-remove-streams")
async def batch_remove_streams(
    req: BatchRemoveStreamRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Bulk-delete embedded streams (audio/subtitle) via ffmpeg remux."""
    results = {"success": [], "failed": []}
    for op in req.operations:
        item_id = op.item_id
        stream_index = op.stream_index
        if not item_id or stream_index < 0:
            results["failed"].append({"item_id": item_id, "error": "invalid_params"})
            continue
        r = await remove_stream(db, item_id, stream_index)
        if r.get("success"):
            results["success"].append({"item_id": item_id, "stream_index": stream_index})
        else:
            results["failed"].append({"item_id": item_id, "error": r.get("error", "unknown")})
    return results
