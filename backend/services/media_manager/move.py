"""Move, deletion et creation de folders."""
import logging
from pathlib import Path

from ._io import _fast_move, _force_delete, _same_device
from ._paths import _validate_name, _validate_path
from .naming import format_size

logger = logging.getLogger("mediakeeper.media_manager")


async def delete_file(path: str):
    err = _validate_path(path)
    if err:
        return {"error": err}

    target = Path(path)
    if not target.exists():
        return {"error": f"not_found: {path}"}

    try:
        await _force_delete(target)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


async def create_folders_batch(folders: list) -> list:
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
        except Exception as e:
            results.append({"parent_path": parent_path, "folder_name": folder_name, "error": str(e)})

    return results


async def move_file(src_path: str, dest_folder: str) -> dict:
    logger.info(f"[MOVE] {src_path!r} → {dest_folder!r}")
    for p in (src_path, dest_folder):
        err = _validate_path(p)
        if err:
            logger.warning(f"[MOVE] Path non allowed : {p!r} — {err}")
            return {"error": err}

    src  = Path(src_path)
    dest = Path(dest_folder)

    if not src.exists():
        logger.warning(f"[MOVE] Source not found: {src_path!r}")
        return {"error": f"source_not_found: {src_path}"}
    if not dest.is_dir():
        logger.warning(f"[MOVE] Invalid destination: {dest_folder!r}")
        return {"error": f"destination_not_a_directory: {dest_folder}"}

    try:
        target = dest / src.name
        same_dev = _same_device(src, dest)
        logger.info(f"[MOVE] same_device={same_dev} | target={target!r}")
        await _fast_move(str(src), str(target))
        logger.info(f"[MOVE] OK : {src_path!r} → {target!r}")
        return {"success": True, "src": src_path, "dest": dest_folder}
    except Exception as e:
        logger.error(f"[MOVE] Error : {e}", exc_info=True)
        return {"error": str(e)}


async def check_move_conflicts(file_names: list[str], dest_folder: str) -> dict:
    """Check si des files existent already in le folder de destination."""
    err = _validate_path(dest_folder)
    if err:
        return {"error": err}

    dest = Path(dest_folder)
    if not dest.is_dir():
        return {"error": f"destination_not_found: {dest_folder}"}

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


async def move_file_overwrite(src_path: str, dest_folder: str) -> dict:
    """Move un file en overwriting si required."""
    logger.info(f"[MOVE-OW] {src_path!r} → {dest_folder!r}")
    for p in (src_path, dest_folder):
        err = _validate_path(p)
        if err:
            logger.warning(f"[MOVE-OW] Path non allowed : {p!r} — {err}")
            return {"error": err}

    src  = Path(src_path)
    dest = Path(dest_folder)

    if not src.exists():
        logger.warning(f"[MOVE-OW] Source not found: {src_path!r}")
        return {"error": f"source_not_found: {src_path}"}
    if not dest.is_dir():
        logger.warning(f"[MOVE-OW] Invalid destination: {dest_folder!r}")
        return {"error": f"destination_not_a_directory: {dest_folder}"}

    try:
        target = dest / src.name
        if target.exists():
            logger.info(f"[MOVE-OW] Deletion target existante : {target!r} (is_dir={target.is_dir()})")
            await _force_delete(target)
            logger.info(f"[MOVE-OW] Target deleted OK")
        same_dev = _same_device(src, dest)
        logger.info(f"[MOVE-OW] same_device={same_dev} | target={target!r}")
        await _fast_move(str(src), str(target))
        logger.info(f"[MOVE-OW] OK : {src_path!r} → {target!r}")
        return {"success": True, "src": src_path, "dest": dest_folder, "overwritten": True}
    except Exception as e:
        logger.error(f"[MOVE-OW] Error : {e}", exc_info=True)
        return {"error": str(e)}
