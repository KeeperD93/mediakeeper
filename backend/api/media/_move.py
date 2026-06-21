"""Endpoints for move, delete and folder creation."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from api.auth import get_current_user
from models.user import User
from services.media_manager import (
    move_file,
    move_file_overwrite,
    check_move_conflicts,
    delete_file,
    create_folders_batch,
    MEDIA_FOLDERS,
)
from services.media_manager._errors import HARD_FAIL_CODES

logger = logging.getLogger("mediakeeper.api.media")
router = APIRouter()


def _raise_if_hard_fail(result: dict) -> None:
    """Map a service-layer hard failure code to a 500 HTTPException.

    Soft validation outcomes (``path_not_allowed``, ``source_not_found``,
    ``destination_not_a_directory``, …) remain in the response body so the
    frontend can surface them as user feedback. The codes listed in
    :data:`HARD_FAIL_CODES` are the only ones promoted to a 500.
    """
    err = result.get("error")
    if err in HARD_FAIL_CODES:
        raise HTTPException(status_code=500, detail=err) from None


class DeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str


class MoveCatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    src_path: str
    src_cat:  str
    dest_cat: str


@router.post("/move-cat")
async def move_cat(req: MoveCatRequest, _: User = Depends(get_current_user)):
    """Move a file from one category to another (cross-category drag)."""
    logger.info("[MOVE-CAT] %r : %s → %s", req.src_path, req.src_cat, req.dest_cat)
    dest_base = MEDIA_FOLDERS.get(req.dest_cat)
    if not dest_base:
        return {"error": "unknown_destination_category"}
    result = await move_file(req.src_path, dest_base)
    _raise_if_hard_fail(result)
    if result.get("error"):
        logger.error("[MOVE-CAT] Failed: %s", result["error"])
    else:
        logger.info("[MOVE-CAT] OK → %s", dest_base)
    return result


@router.post("/delete")
async def delete(req: DeleteRequest, _: User = Depends(get_current_user)):
    logger.info("[DELETE] %s", req.path)
    result = await delete_file(req.path)
    _raise_if_hard_fail(result)
    if result.get("error"):
        logger.error("[DELETE] Failed: %s", result["error"])
    else:
        logger.info("[DELETE] OK")
    return result


class BatchDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paths: list[str] = Field(max_length=1000)


@router.post("/delete-batch")
async def delete_batch(req: BatchDeleteRequest, _: User = Depends(get_current_user)):
    """Delete several files/folders at once."""
    logger.info("[DELETE-BATCH] %s items", len(req.paths))
    results = []
    for p in req.paths:
        r = await delete_file(p)
        results.append({"path": p, **(r or {})})
    errors = [r for r in results if r.get("error")]
    if errors:
        logger.warning("[DELETE-BATCH] %s errors out of %s", len(errors), len(req.paths))
    return {"results": results, "deleted": len(results) - len(errors), "errors": len(errors)}


class FolderItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parent_path: str
    folder_name: str


class CreateFoldersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    folders: list[FolderItem]


@router.post("/create-folders")
async def create_folders(req: CreateFoldersRequest, _: User = Depends(get_current_user)):
    logger.info("[CREATE-FOLDERS] %s folders", len(req.folders))
    items = [{"parent_path": f.parent_path, "folder_name": f.folder_name} for f in req.folders]
    result = await create_folders_batch(items)
    _raise_if_hard_fail(result)
    return result


class MoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    src_path:    str
    dest_folder: str


@router.post("/move")
async def move(req: MoveRequest, _: User = Depends(get_current_user)):
    logger.info("[MOVE] %s → %s", req.src_path, req.dest_folder)
    result = await move_file(req.src_path, req.dest_folder)
    _raise_if_hard_fail(result)
    if result.get("error"):
        logger.error("[MOVE] Failed: %s", result["error"])
    else:
        logger.info("[MOVE] OK")
    return result


class CheckConflictsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_names: list[str]
    dest_folder: str


@router.post("/check-move-conflicts")
async def check_conflicts(req: CheckConflictsRequest, _: User = Depends(get_current_user)):
    """Check whether files already exist at the destination."""
    logger.info("[CHECK-CONFLICTS] %s files → %s", len(req.file_names), req.dest_folder)
    result = await check_move_conflicts(req.file_names, req.dest_folder)
    _raise_if_hard_fail(result)
    return result


class MoveOverwriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    src_path: str
    dest_folder: str


@router.post("/move-overwrite")
async def move_overwrite(req: MoveOverwriteRequest, _: User = Depends(get_current_user)):
    """Move a file, overwriting the existing one."""
    logger.info("[MOVE-OVERWRITE] %s → %s", req.src_path, req.dest_folder)
    result = await move_file_overwrite(req.src_path, req.dest_folder)
    _raise_if_hard_fail(result)
    if result.get("error"):
        logger.error("[MOVE-OVERWRITE] Failed: %s", result["error"])
    else:
        logger.info("[MOVE-OVERWRITE] OK")
    return result
