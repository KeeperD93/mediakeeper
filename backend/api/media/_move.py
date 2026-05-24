"""Endpoints for move, delete and folder creation."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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

logger = logging.getLogger("mediakeeper.api.media")
router = APIRouter()


class DeleteRequest(BaseModel):
    path: str


class MoveCatRequest(BaseModel):
    src_path: str
    src_cat:  str
    dest_cat: str


@router.post("/move-cat")
async def move_cat(req: MoveCatRequest, _: User = Depends(get_current_user)):
    """Move a file from one category to another (cross-category drag)."""
    logger.info(f"[MOVE-CAT] {req.src_path!r} : {req.src_cat} → {req.dest_cat}")
    dest_base = MEDIA_FOLDERS.get(req.dest_cat)
    if not dest_base:
        return {"error": "unknown_destination_category"}
    try:
        result = await move_file(req.src_path, dest_base)
        if result.get("error"):
            logger.error(f"[MOVE-CAT] Failed: {result['error']}")
        else:
            logger.info(f"[MOVE-CAT] OK → {dest_base}")
        return result
    except Exception:
        logger.exception("[MOVE-CAT] failed")
        raise HTTPException(status_code=500, detail="move_failed") from None


@router.post("/delete")
async def delete(req: DeleteRequest, _: User = Depends(get_current_user)):
    logger.info(f"[DELETE] {req.path}")
    try:
        result = await delete_file(req.path)
        if result.get("error"):
            logger.error(f"[DELETE] Failed: {result['error']}")
        else:
            logger.info("[DELETE] OK")
        return result
    except Exception:
        logger.exception("[DELETE] failed")
        raise HTTPException(status_code=500, detail="delete_failed") from None


class BatchDeleteRequest(BaseModel):
    paths: list[str]


@router.post("/delete-batch")
async def delete_batch(req: BatchDeleteRequest, _: User = Depends(get_current_user)):
    """Supprime several files/folders d'un coup."""
    logger.info(f"[DELETE-BATCH] {len(req.paths)} items")
    results = []
    for p in req.paths:
        try:
            r = await delete_file(p)
            results.append({"path": p, **(r or {})})
        except Exception:
            logger.exception("[DELETE-BATCH] item %r failed", p)
            results.append({"path": p, "error": "delete_failed"})
    errors = [r for r in results if r.get("error")]
    if errors:
        logger.warning(f"[DELETE-BATCH] {len(errors)} errors sur {len(req.paths)}")
    return {"results": results, "deleted": len(results) - len(errors), "errors": len(errors)}


class FolderItem(BaseModel):
    parent_path: str
    folder_name: str


class CreateFoldersRequest(BaseModel):
    folders: List[FolderItem]


@router.post("/create-folders")
async def create_folders(req: CreateFoldersRequest, _: User = Depends(get_current_user)):
    logger.info(f"[CREATE-FOLDERS] {len(req.folders)} folders")
    items = [{"parent_path": f.parent_path, "folder_name": f.folder_name} for f in req.folders]
    try:
        result = await create_folders_batch(items)
        return result
    except Exception:
        logger.exception("[CREATE-FOLDERS] failed")
        raise HTTPException(status_code=500, detail="create_folders_failed") from None


class MoveRequest(BaseModel):
    src_path:    str
    dest_folder: str


@router.post("/move")
async def move(req: MoveRequest, _: User = Depends(get_current_user)):
    logger.info(f"[MOVE] {req.src_path} → {req.dest_folder}")
    try:
        result = await move_file(req.src_path, req.dest_folder)
        if result.get("error"):
            logger.error(f"[MOVE] Failed: {result['error']}")
        else:
            logger.info("[MOVE] OK")
        return result
    except Exception:
        logger.exception("[MOVE] failed")
        raise HTTPException(status_code=500, detail="move_failed") from None


class CheckConflictsRequest(BaseModel):
    file_names: List[str]
    dest_folder: str


@router.post("/check-move-conflicts")
async def check_conflicts(req: CheckConflictsRequest, _: User = Depends(get_current_user)):
    """Check whether files already exist at the destination."""
    logger.info(f"[CHECK-CONFLICTS] {len(req.file_names)} files → {req.dest_folder}")
    try:
        result = await check_move_conflicts(req.file_names, req.dest_folder)
        return result
    except Exception:
        logger.exception("[CHECK-CONFLICTS] failed")
        raise HTTPException(status_code=500, detail="check_conflicts_failed") from None


class MoveOverwriteRequest(BaseModel):
    src_path: str
    dest_folder: str


@router.post("/move-overwrite")
async def move_overwrite(req: MoveOverwriteRequest, _: User = Depends(get_current_user)):
    """Move a file, overwriting the existing one."""
    logger.info(f"[MOVE-OVERWRITE] {req.src_path} → {req.dest_folder}")
    try:
        result = await move_file_overwrite(req.src_path, req.dest_folder)
        if result.get("error"):
            logger.error(f"[MOVE-OVERWRITE] Failed: {result['error']}")
        else:
            logger.info("[MOVE-OVERWRITE] OK")
        return result
    except Exception:
        logger.exception("[MOVE-OVERWRITE] failed")
        raise HTTPException(status_code=500, detail="move_overwrite_failed") from None
