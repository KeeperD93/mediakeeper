"""Endpoints de navigation/listing (files, rootpath, browse-dirs)."""
import logging
from pathlib import Path
from fastapi import APIRouter, Depends

from api.auth import get_current_user
from models.user import User
from services.media_manager import list_files, MEDIA_FOLDERS
from services.path_config import validate_path_in_roots

from ._helpers import _get_browse_roots

logger = logging.getLogger("mediakeeper.api.media")
router = APIRouter()


@router.get("/files/{folder_key}")
async def get_files(folder_key: str, subpath: str = "", _: User = Depends(get_current_user)):
    logger.info(f"[BROWSE] folder={folder_key} subpath={subpath!r}")
    try:
        result = await list_files(folder_key, subpath)
        return result
    except Exception as e:
        logger.error(f"[BROWSE] Error folder={folder_key} subpath={subpath!r}: {e}")
        raise


@router.get("/rootpath/{folder_key}")
async def get_rootpath(folder_key: str, _: User = Depends(get_current_user)):
    """Return the absolute NAS path for a category (useful for cross-category D&D)."""
    path = MEDIA_FOLDERS.get(folder_key)
    if not path:
        return {"error": "unknown_category"}
    return {"path": path, "key": folder_key}


@router.get("/browse-dirs")
async def browse_dirs(
    path: str = "/",
    _: User = Depends(get_current_user),
):
    """Liste les sous-folders d'un path for le browser de folders."""
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
    if error:
        if error == "path_not_found":
            error = "directory_not_found"
        return {"path": normalized_path, "dirs": [], "error": error}
    dirs = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: e.name.lower()):
            if not entry.is_dir():
                continue
            name = entry.name
            if name.startswith('.') or name.startswith('@') or name.startswith('$'):
                continue
            dirs.append({"name": name, "path": str(entry)})
    except PermissionError:
        return {"path": path, "dirs": [], "error": "permission_denied"}
    return {"path": path, "dirs": dirs}
