"""Move, deletion et creation de folders."""
import logging
from pathlib import Path

from ._io import _fast_move, _force_delete, _same_device
from ._paths import _validate_name, _validate_path
from .naming import format_size

logger = logging.getLogger("mediakeeper.media_manager")


async def delete_file(path: str) -> dict:
    err = _validate_path(path)
    if err:
        return {"error": err}

    target = Path(path)
    if not target.exists():
        return {"error": f"not_found: {path}"}

    try:
        await _force_delete(target)
        return {"success": True}
    except Exception:
        logger.exception("[DELETE] failed")
        return {"error": "delete_failed"}


async def create_folders_batch(folders: list) -> dict:
    """Create the folders described in ``folders``.

    Always returns a ``dict`` for a uniform service contract: ``{"results":
    [...]}`` on the nominal path (each item carries its own ``success`` or
    soft ``error`` code), ``{"error": "create_folders_failed", "results":
    []}`` only if an unexpected exception escapes the per-item loop.
    """
    try:
        results = []
        for f in folders:
            parent_path = f["parent_path"]
            folder_name = f["folder_name"]

            err = _validate_path(parent_path)
            if err:
                results.append({"parent_path": parent_path, "folder_name": folder_name, "error": err})
                continue

            name_err = _validate_name(folder_name)
            if name_err:
                results.append({"parent_path": parent_path, "folder_name": folder_name, "error": name_err})
                continue

            parent = Path(parent_path).resolve()
            target = parent / folder_name
            target_resolved = target.resolve(strict=False)
            if target_resolved.parent != parent:
                results.append({"parent_path": parent_path, "folder_name": folder_name, "error": "path_not_allowed"})
                continue

            already = target.exists()
            try:
                target.mkdir(parents=True, exist_ok=True)
                results.append({
                    "parent_path": parent_path,
                    "folder_name": folder_name,
                    "success":     True,
                    "path":        str(target_resolved),
                    "already_existed": already,
                })
            except Exception:
                logger.exception("[CREATE_FOLDER] failed for %s/%s", parent_path, folder_name)
                results.append({
                    "parent_path": parent_path,
                    "folder_name": folder_name,
                    "error": "create_folder_failed",
                })

        return {"results": results}
    except Exception:
        logger.exception("[CREATE_FOLDERS] batch failed")
        return {"error": "create_folders_failed", "results": []}


async def move_file(src_path: str, dest_folder: str) -> dict:
    logger.info("[MOVE] %r → %r", src_path, dest_folder)
    for p in (src_path, dest_folder):
        err = _validate_path(p)
        if err:
            logger.warning("[MOVE] Path non allowed : %r — %s", p, err)
            return {"error": err}

    src  = Path(src_path)
    dest = Path(dest_folder)

    if not src.exists():
        logger.warning("[MOVE] Source not found: %r", src_path)
        return {"error": f"source_not_found: {src_path}"}
    if not dest.is_dir():
        logger.warning("[MOVE] Invalid destination: %r", dest_folder)
        return {"error": f"destination_not_a_directory: {dest_folder}"}

    try:
        target = dest / src.name
        same_dev = _same_device(src, dest)
        logger.info("[MOVE] same_device=%s | target=%r", same_dev, target)
        await _fast_move(str(src), str(target))
        logger.info("[MOVE] OK : %r → %r", src_path, target)
        return {"success": True, "src": src_path, "dest": dest_folder}
    except Exception:
        logger.exception("[MOVE] failed")
        return {"error": "move_failed"}


async def check_move_conflicts(file_names: list[str], dest_folder: str) -> dict:
    """Check si des files existent already in le folder de destination."""
    err = _validate_path(dest_folder)
    if err:
        return {"error": err}

    dest = Path(dest_folder)
    if not dest.is_dir():
        return {"error": f"destination_not_found: {dest_folder}"}

    try:
        conflicts = []
        dest_resolved = dest.resolve(strict=False)
        for name in file_names:
            name_err = _validate_name(name)
            if name_err:
                return {"error": name_err}
            target = dest / name
            target_resolved = target.resolve(strict=False)
            if target_resolved.parent != dest_resolved:
                return {"error": "path_not_allowed"}
            if target.exists():
                size = target.stat().st_size if target.is_file() else 0
                conflicts.append({
                    "name": name,
                    "existing_path": str(target_resolved),
                    "existing_size": size,
                    "existing_size_label": format_size(size) if size else "-",
                })
        return {"conflicts": conflicts}
    except Exception:
        logger.exception("[CHECK_CONFLICTS] failed")
        return {"error": "check_conflicts_failed"}


async def move_file_overwrite(src_path: str, dest_folder: str) -> dict:
    """Move un file en overwriting si required."""
    logger.info("[MOVE-OW] %r → %r", src_path, dest_folder)
    for p in (src_path, dest_folder):
        err = _validate_path(p)
        if err:
            logger.warning("[MOVE-OW] Path non allowed : %r — %s", p, err)
            return {"error": err}

    src  = Path(src_path)
    dest = Path(dest_folder)

    if not src.exists():
        logger.warning("[MOVE-OW] Source not found: %r", src_path)
        return {"error": f"source_not_found: {src_path}"}
    if not dest.is_dir():
        logger.warning("[MOVE-OW] Invalid destination: %r", dest_folder)
        return {"error": f"destination_not_a_directory: {dest_folder}"}

    try:
        target = dest / src.name
        if target.exists():
            logger.info("[MOVE-OW] Deletion target existante : %r (is_dir=%s)", target, target.is_dir())
            await _force_delete(target)
            logger.info("[MOVE-OW] Target deleted OK")
        same_dev = _same_device(src, dest)
        logger.info("[MOVE-OW] same_device=%s | target=%r", same_dev, target)
        await _fast_move(str(src), str(target))
        logger.info("[MOVE-OW] OK : %r → %r", src_path, target)
        return {"success": True, "src": src_path, "dest": dest_folder, "overwritten": True}
    except Exception:
        logger.exception("[MOVE-OW] failed")
        return {"error": "move_overwrite_failed"}
