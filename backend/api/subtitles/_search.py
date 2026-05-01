"""Search + download a subtitle + existing subtitles."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from core.http_client import get_internal_client
from models.user import User
from services.opensubtitles import (
    _get_local_path_roots,
    _resolve_local_path,
    compute_file_hash,
    delete_external_subtitle,
    download_subtitle,
    get_existing_subtitles,
    remove_stream,
    search_subtitles,
)
from services.path_config import validate_path_in_roots
from services.subtitle_history import record_download as svc_record_download

from ._schemas import (
    DeleteRequest,
    DownloadRequest,
    RemoveStreamRequest,
    RemoveStreamsBatchRequest,
    SearchRequest,
)

logger = logging.getLogger("mediakeeper.api.subtitles")
router = APIRouter()


@router.post("/search")
async def search(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    moviehash = ""
    if req.file_path and req.file_path.strip():
        local_path = await _resolve_local_path(db, req.file_path)
        roots = await _get_local_path_roots(db)
        resolved, error = validate_path_in_roots(
            local_path,
            allow_missing=False,
            must_be_dir=False,
            roots=roots,
            label="Subtitle source",
        )
        if error:
            raise HTTPException(status_code=400, detail=error)
        moviehash = compute_file_hash(str(resolved)) or ""

    return await search_subtitles(
        db, query=req.query, imdb_id=req.imdb_id, tmdb_id=req.tmdb_id,
        season=req.season, episode=req.episode,
        languages=req.languages, moviehash=moviehash,
    )


@router.post("/download")
async def download(
    req: DownloadRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await download_subtitle(db, req.file_id, req.destination, req.media_duration_sec)

    if result.get("success") and req.item_id:
        # Refresh Emby
        try:
            from services.emby import _get_emby_config
            cfg = await _get_emby_config(db)
            if cfg:
                url, api_key = cfg
                client = get_internal_client()
                await client.post(
                    f"{url}/Items/{req.item_id}/Refresh",
                    headers={"X-Emby-Token": api_key}, timeout=10.0,
                )
        except Exception:
            pass

        try:
            history_data = {
                "emby_item_id":       req.item_id,
                "media_name":         req.media_name or "",
                "media_type":         req.media_type or "",
                "series_name":        req.series_name or None,
                "season":             req.season or None,
                "episode":            req.episode or None,
                "os_file_id":         req.file_id,
                "os_subtitle_id":     req.subtitle_id or "",
                "file_name":          req.file_name or "",
                "language":           req.language or "",
                "destination":        req.destination,
                "file_size":          result.get("size"),
                "quality_score":      req.quality_score or None,
                "hash_match":         req.hash_match or False,
                "hearing_impaired":   req.hearing_impaired or False,
                "foreign_parts_only": req.foreign_parts_only or False,
                "from_trusted":       req.from_trusted or False,
                "ai_translated":      req.ai_translated or False,
            }
            await svc_record_download(db, **history_data)
        except Exception as e:
            logger.warning(f"[subtitles] Failed to record download history: {e}")

    return result


@router.get("/existing/{item_id}")
async def existing(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_existing_subtitles(db, item_id)


@router.post("/delete")
async def delete_sub(
    req: DeleteRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return delete_external_subtitle(req.path)


@router.post("/remove-stream")
async def remove_stream_route(
    req: RemoveStreamRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Supprime un stream audio ou sous-titre embedded via ffmpeg remux."""
    return await remove_stream(db, req.item_id, req.stream_index)


@router.post("/remove-streams-batch")
async def remove_streams_batch_route(
    req: RemoveStreamsBatchRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Supprime several streams en un seul remux ffmpeg."""
    from services.opensubtitles import remove_streams_batch
    return await remove_streams_batch(db, req.item_id, req.stream_indices)
