"""Endpoints de navigation/listing (files, rootpath, browse-dirs)."""
import asyncio
import logging
from pathlib import Path
from fastapi import APIRouter, Depends

from api.auth import get_current_user
from models.user import User
from services.media_manager import MEDIA_FOLDERS, list_files
from services.path_config import is_path_within_backup_dir, validate_path_in_roots

from ._helpers import _get_browse_roots

logger = logging.getLogger("mediakeeper.api.media")
router = APIRouter()


@router.get("/files/{folder_key}")
async def get_files(folder_key: str, subpath: str = "", _: User = Depends(get_current_user)):
    logger.info("[BROWSE] folder=%s subpath=%r", folder_key, subpath)
    try:
        result = await list_files(folder_key, subpath)
        return result
    except Exception:
        logger.exception("[BROWSE] Error folder=%s subpath=%r", folder_key, subpath)
        raise


@router.get("/rootpath/{folder_key}")
async def get_rootpath(folder_key: str, _: User = Depends(get_current_user)):
    """Return the absolute NAS path for a category (useful for cross-category D&D)."""
    path = MEDIA_FOLDERS.get(folder_key)
    if not path:
        return {"error": "unknown_category"}
    return {"path": path, "key": folder_key}


def _list_subdirs(target: Path) -> list[dict]:
    """Synchronous sub-folder scan, offloaded via ``asyncio.to_thread``:
    ``iterdir`` + per-entry ``is_dir`` and backup-zone checks block the event
    loop on large NAS directories."""
    dirs = []
    for entry in sorted(target.iterdir(), key=lambda e: e.name.lower()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith('.') or name.startswith('@') or name.startswith('$'):
            continue
        # Never surface the backup zone, even when it sits inside a media root.
        if is_path_within_backup_dir(entry):
            continue
        dirs.append({"name": name, "path": str(entry)})
    return dirs


@router.get("/browse-dirs")
async def browse_dirs(
    path: str = "/",
    _: User = Depends(get_current_user),
):
    """List sub-folders of a path for the folder browser."""
    normalized_path = (path or "/").strip()
    if normalized_path in ("", "/"):
        return {"path": "/", "dirs": _get_browse_roots()}

    browse_roots = [Path(item["path"]) for item in _get_browse_roots()]
    target, error = validate_path_in_roots(
        normalized_path,
        allow_missing=False,
        must_be_dir=True,
        roots=browse_roots,
        label="Browse path",
    )
    # Refuse to descend into the backup zone even when it lives under a media
    # root (validate_path_in_roots accepts it as a child of that root).
    if not error and is_path_within_backup_dir(target):
        error = "directory_not_found"
    if error:
        if error == "path_not_found":
            error = "directory_not_found"
        return {"path": normalized_path, "dirs": [], "error": error}
    try:
        dirs = await asyncio.to_thread(_list_subdirs, target)
    except PermissionError:
        return {"path": path, "dirs": [], "error": "permission_denied"}
    return {"path": path, "dirs": dirs}
