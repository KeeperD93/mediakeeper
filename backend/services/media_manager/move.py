"""Move, delete and create folders."""
import logging

from ._io import _fast_move, _force_delete, _same_device
from ._paths import _ensure_within_media_roots, _validate_name
from .naming import format_size

logger = logging.getLogger("mediakeeper.media_manager")


async def delete_file(path: str) -> dict:
    target = _ensure_within_media_roots(path)
    if target is None:
        return {"error": "path_not_allowed"}

    if not target.exists():
        return {"error": "not_found"}

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

            parent = _ensure_within_media_roots(parent_path)
            if parent is None:
                results.append({"parent_path": parent_path, "folder_name": folder_name, "error": "path_not_allowed"})
                continue

            name_err = _validate_name(folder_name)
            if name_err:
                results.append({"parent_path": parent_path, "folder_name": folder_name, "error": name_err})
                continue

            target_candidate = parent / folder_name
            target = target_candidate.resolve(strict=False)
            try:
                target.relative_to(parent)
            except ValueError:
                results.append({"parent_path": parent_path, "folder_name": folder_name, "error": "path_not_allowed"})
                continue

            already = target.exists()
            try:
                target.mkdir(parents=True, exist_ok=True)
                results.append({
                    "parent_path": parent_path,
                    "folder_name": folder_name,
                    "success":     True,
                    "path":        str(target),
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
    src = _ensure_within_media_roots(src_path)
    dest = _ensure_within_media_roots(dest_folder)
    if src is None or dest is None:
        logger.warning("[MOVE] Containment rejected: src=%r dest=%r", src_path, dest_folder)
        return {"error": "path_not_allowed"}

    if not src.exists():
        logger.warning("[MOVE] Source not found: %r", src_path)
        return {"error": "source_not_found"}
    if not dest.is_dir():
        logger.warning("[MOVE] Invalid destination: %r", dest_folder)
        return {"error": "destination_not_a_directory"}

    try:
        target_candidate = dest / src.name
        target = target_candidate.resolve(strict=False)
        try:
            target.relative_to(dest)
        except ValueError:
            logger.warning("[MOVE] Target escape: %r", target_candidate)
            return {"error": "path_not_allowed"}
        same_dev = _same_device(src, dest)
        logger.info("[MOVE] same_device=%s | target=%r", same_dev, target)
        await _fast_move(str(src), str(target))
        logger.info("[MOVE] OK : %r → %r", src_path, target)
        return {"success": True, "src": src_path, "dest": dest_folder}
    except Exception:
        logger.exception("[MOVE] failed")
        return {"error": "move_failed"}


async def check_move_conflicts(file_names: list[str], dest_folder: str) -> dict:
    """Check whether files already exist in the destination folder."""
    dest = _ensure_within_media_roots(dest_folder)
    if dest is None:
        return {"error": "path_not_allowed"}

    if not dest.is_dir():
        return {"error": "destination_not_found"}

    try:
        conflicts = []
        for name in file_names:
            name_err = _validate_name(name)
            if name_err:
                return {"error": name_err}
            target_candidate = dest / name
            target = target_candidate.resolve(strict=False)
            try:
                target.relative_to(dest)
            except ValueError:
                return {"error": "path_not_allowed"}
            if target.exists():
                size = target.stat().st_size if target.is_file() else 0
                conflicts.append({
                    "name": name,
                    "existing_path": str(target),
                    "existing_size": size,
                    "existing_size_label": format_size(size) if size else "-",
                })
        return {"conflicts": conflicts}
    except Exception:
        logger.exception("[CHECK_CONFLICTS] failed")
        return {"error": "check_conflicts_failed"}


async def move_file_overwrite(src_path: str, dest_folder: str) -> dict:
    """Move a file, overwriting the destination if required."""
    logger.info("[MOVE-OW] %r → %r", src_path, dest_folder)
    src = _ensure_within_media_roots(src_path)
    dest = _ensure_within_media_roots(dest_folder)
    if src is None or dest is None:
        logger.warning("[MOVE-OW] Containment rejected: src=%r dest=%r", src_path, dest_folder)
        return {"error": "path_not_allowed"}

    if not src.exists():
        logger.warning("[MOVE-OW] Source not found: %r", src_path)
        return {"error": "source_not_found"}
    if not dest.is_dir():
        logger.warning("[MOVE-OW] Invalid destination: %r", dest_folder)
        return {"error": "destination_not_a_directory"}

    try:
        target_candidate = dest / src.name
        target = target_candidate.resolve(strict=False)
        try:
            target.relative_to(dest)
        except ValueError:
            logger.warning("[MOVE-OW] Target escape: %r", target_candidate)
            return {"error": "path_not_allowed"}
        if target.exists():
            logger.info("[MOVE-OW] Deleting existing target: %r (is_dir=%s)", target, target.is_dir())
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
