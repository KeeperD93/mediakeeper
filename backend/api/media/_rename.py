"""Renaming endpoints (files + folders) and name-building helpers."""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

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

# Filesystem upper bounds used as request-level guards. POSIX caps the
# full path at 4096 bytes and a single component at 255 bytes — going
# higher serves no legitimate purpose and merely widens the surface
# fed to downstream sanitisers (defence in depth against the
# polynomial-degree regex class CodeQL flagged in `services.media_manager`).
_MAX_PATH_LEN = 4096
_MAX_NAME_LEN = 255
_MAX_TITLE_LEN = 500
_MAX_QUALITY_LEN = 50
_MAX_EXT_LEN = 10
_MAX_CATEGORY_LEN = 100
_MAX_BATCH_ITEMS = 500


class RenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    old_path: str = Field(..., max_length=_MAX_PATH_LEN)
    new_name: str = Field(..., min_length=1, max_length=_MAX_NAME_LEN)


class RenameBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[RenameRequest] = Field(..., max_length=_MAX_BATCH_ITEMS)
    cat: str = Field("", max_length=_MAX_CATEGORY_LEN)


@router.post("/preview")
async def preview(req: RenameRequest, _: User = Depends(get_current_user)):
    return preview_rename(req.old_path, req.new_name)


@router.post("/rename")
async def rename(req: RenameRequest, _: User = Depends(get_current_user)):
    logger.info("[RENAME] %s → %s", req.old_path, req.new_name)
    try:
        result = await apply_rename(req.old_path, req.new_name)
        if result.get("error"):
            logger.error("[RENAME] Failed: %s", result["error"])
        else:
            logger.info("[RENAME] OK: %s", result.get("new_path", ""))
        return result
    except Exception as e:
        logger.error("[RENAME] Exception: %s", e)
        raise


@router.post("/rename-batch")
async def rename_batch(req: RenameBatchRequest, _: User = Depends(get_current_user)):
    logger.info("[RENAME-BATCH] %s files, cat=%r", len(req.items), req.cat)
    items = [{"old_path": r.old_path, "new_name": r.new_name} for r in req.items]
    if items:
        logger.info(
            "[RENAME-BATCH] First item: old_path=%r new_name=%r",
            items[0]["old_path"], items[0]["new_name"],
        )
    try:
        result = await apply_rename_batch(items, cat=req.cat)
        errors = [r for r in result if r.get("error")]
        if errors:
            logger.warning(
                "[RENAME-BATCH] %s errors out of %s", len(errors), len(req.items),
            )
            for err in errors[:3]:
                logger.warning(
                    "[RENAME-BATCH] Detail: old_path=%s error=%s",
                    err.get("old_path", "?"), err.get("error", "?"),
                )
        else:
            logger.info("[RENAME-BATCH] OK: %s files renamed", len(req.items))
        return result
    except Exception as e:
        logger.error("[RENAME-BATCH] Exception: %s", e)
        raise


class MovieNameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title:   str = Field(..., min_length=1, max_length=_MAX_TITLE_LEN)
    year:    str = Field("", max_length=10)
    quality: str = Field("", max_length=_MAX_QUALITY_LEN)
    ext:     str = Field("", max_length=_MAX_EXT_LEN)


class EpisodeNameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    series:  str = Field(..., min_length=1, max_length=_MAX_TITLE_LEN)
    season:  int = Field(..., ge=0, le=999)
    episode: int = Field(..., ge=0, le=9999)
    title:   str = Field(..., min_length=1, max_length=_MAX_TITLE_LEN)
    ext:     str = Field("", max_length=_MAX_EXT_LEN)


@router.post("/build/movie")
async def build_movie(req: MovieNameRequest, _: User = Depends(get_current_user)):
    return {"name": build_movie_name(req.title, req.year, req.quality, req.ext)}


@router.post("/build/episode")
async def build_episode(req: EpisodeNameRequest, _: User = Depends(get_current_user)):
    return {"name": build_episode_name(req.series, req.season, req.episode, req.title, req.ext)}


class RenameFolderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cat:      str = Field(..., max_length=_MAX_CATEGORY_LEN)   # category key (e.g. "telechargement")
    subpath:  str = Field(..., max_length=_MAX_PATH_LEN)        # current relative path
    new_name: str = Field(..., min_length=1, max_length=_MAX_NAME_LEN)  # new folder name


@router.post("/rename-folder")
async def rename_folder(req: RenameFolderRequest, _: User = Depends(get_current_user)):
    """Rename a folder by building the absolute path on the backend side."""
    logger.info(
        "[RENAME-FOLDER] cat=%s subpath=%r → %s",
        req.cat, req.subpath, req.new_name,
    )
    base = MEDIA_FOLDERS.get(req.cat)
    if not base:
        logger.error("[RENAME-FOLDER] Unknown category : %s", req.cat)
        return {"error": f"Unknown category: {req.cat}"}

    abs_path = str(Path(base) / req.subpath.strip("/\\"))

    err = _validate_path(abs_path)
    if err:
        return {"error": err}

    result = await apply_rename_batch([{"old_path": abs_path, "new_name": req.new_name}])
    return result[0] if result else {"error": "no_result"}
