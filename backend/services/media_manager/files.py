"""List files in a media category."""
import logging
from pathlib import Path

from ._paths import VIDEO_EXTENSIONS, _validate_path
from .categories import MEDIA_FOLDERS
from .naming import format_size
from services.path_config import is_path_within_backup_dir

logger = logging.getLogger("mediakeeper.media_manager.files")


async def list_files(folder_key: str, subpath: str = "") -> dict | list[dict]:
    folder_base = MEDIA_FOLDERS.get(folder_key)
    if not folder_base:
        return {"error": "unknown_folder"}

    target = Path(folder_base)
    if subpath:
        clean_sub = subpath.strip('/')
        if '..' in clean_sub.split('/'):
            return {"error": "path_not_allowed"}
        target = target / clean_sub

    target_str = str(target)
    err = _validate_path(target_str)
    if err:
        return {"error": err}

    if not target.exists():
        logger.warning("[files] directory not found: %r", target_str)
        return {"error": "directory_not_found"}

    if not target.is_dir():
        logger.warning("[files] not a directory: %r", target_str)
        return {"error": "not_a_directory"}

    try:
        items = []
        for entry in sorted(target.iterdir(), key=lambda e: e.name.lower()):
            name = entry.name
            if name.startswith('.') or name == '@eaDir' or name.startswith('@'):
                continue

            # Hide entries that fall into the backup zone, even when the
            # backup directory legitimately lives inside a media root: the
            # backup ZIPs must never be browsable through media-manager.
            try:
                entry_resolved = entry.resolve(strict=False)
            except (OSError, RuntimeError):
                continue
            if is_path_within_backup_dir(entry_resolved):
                continue

            if entry.is_dir():
                items.append({
                    "name":       name,
                    "path":       str(entry),
                    "type":       "folder",
                    "size":       0,
                    "size_label": "-",
                    "mtime":      entry.stat().st_mtime,
                })
            elif entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS:
                st = entry.stat()
                items.append({
                    "name":       name,
                    "path":       str(entry),
                    "type":       "file",
                    "size":       st.st_size,
                    "size_label": format_size(st.st_size),
                    "mtime":      st.st_mtime,
                })

        return items

    except PermissionError:
        logger.warning("[files] permission denied: %r", target_str)
        return {"error": "permission_denied"}
    except Exception:
        logger.exception("[files] list_files failed for %r", target_str)
        return {"error": "list_failed"}
