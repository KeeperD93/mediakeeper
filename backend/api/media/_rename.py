"""Renaming endpoints (files + folders) and name-building helpers."""
import logging
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import get_current_user
from models.user import User
from services.media_manager import (
    preview_rename,
    apply_rename,
    apply_rename_batch,
    build_movie_name,
    build_episode_name,
    MEDIA_FOLDERS,
    _validate_path,
)

logger = logging.getLogger("mediakeeper.api.media")
router = APIRouter()


class RenameRequest(BaseModel):
    old_path: str
    new_name: str


class RenameBatchRequest(BaseModel):
    items: List[RenameRequest]
    cat: str = ""


@router.post("/preview")
async def preview(req: RenameRequest, _: User = Depends(get_current_user)):
    return preview_rename(req.old_path, req.new_name)


@router.post("/rename")
async def rename(req: RenameRequest, _: User = Depends(get_current_user)):
    logger.info(f"[RENAME] {req.old_path} → {req.new_name}")
    try:
        result = await apply_rename(req.old_path, req.new_name)
        if result.get("error"):
            logger.error(f"[RENAME] Failed: {result['error']}")
        else:
            logger.info(f"[RENAME] OK: {result.get('new_path', '')}")
        return result
    except Exception as e:
        logger.error(f"[RENAME] Exception: {e}")
        raise


@router.post("/rename-batch")
async def rename_batch(req: RenameBatchRequest, _: User = Depends(get_current_user)):
    logger.info(f"[RENAME-BATCH] {len(req.items)} files, cat={req.cat!r}")
    items = [{"old_path": r.old_path, "new_name": r.new_name} for r in req.items]
    if items:
        logger.info(f"[RENAME-BATCH] First item: old_path={items[0]['old_path']!r} new_name={items[0]['new_name']!r}")
    try:
        result = await apply_rename_batch(items, cat=req.cat)
        errors = [r for r in result if r.get("error")]
        if errors:
            logger.warning(f"[RENAME-BATCH] {len(errors)} errors out of {len(req.items)}")
            for e in errors[:3]:
                logger.warning(f"[RENAME-BATCH] Detail: old_path={e.get('old_path','?')} error={e.get('error','?')}")
        else:
            logger.info(f"[RENAME-BATCH] OK: {len(req.items)} files renamed")
        return result
    except Exception as e:
        logger.error(f"[RENAME-BATCH] Exception: {e}")
        raise


class MovieNameRequest(BaseModel):
    title:   str
    year:    str
    quality: str = ""
    ext:     str = ""


class EpisodeNameRequest(BaseModel):
    series:  str
    season:  int
    episode: int
    title:   str
    ext:     str = ""


@router.post("/build/movie")
async def build_movie(req: MovieNameRequest, _: User = Depends(get_current_user)):
    return {"name": build_movie_name(req.title, req.year, req.quality, req.ext)}


@router.post("/build/episode")
async def build_episode(req: EpisodeNameRequest, _: User = Depends(get_current_user)):
    return {"name": build_episode_name(req.series, req.season, req.episode, req.title, req.ext)}


class RenameFolderRequest(BaseModel):
    cat:      str   # category key (e.g. "telechargement")
    subpath:  str   # current relative path
    new_name: str   # new folder name


@router.post("/rename-folder")
async def rename_folder(req: RenameFolderRequest, _: User = Depends(get_current_user)):
    """Rename a folder by building the absolute path on the backend side."""
    logger.info(f"[RENAME-FOLDER] cat={req.cat} subpath={req.subpath!r} → {req.new_name}")
    base = MEDIA_FOLDERS.get(req.cat)
    if not base:
        logger.error(f"[RENAME-FOLDER] Unknown category : {req.cat}")
        return {"error": f"Unknown category: {req.cat}"}

    abs_path = f"{base}/{req.subpath.strip('/')}"

    err = _validate_path(abs_path)
    if err:
        return {"error": err}

    result = await apply_rename_batch([{"old_path": abs_path, "new_name": req.new_name}])
    return result[0] if result else {"error": "no_result"}
