"""Renaming of files/folders + merge of same-named folders."""
import logging
from pathlib import Path

from ._io import _fast_move, _force_delete
from ._paths import _media_roots, _sanitize_name, _validate_name, _validate_path
from .categories import MEDIA_FOLDERS

logger = logging.getLogger("mediakeeper.media_manager")


async def _merge_folder_into(src_path: str, dest_path: str) -> dict:
    """Merge src into dest, then delete src — only if every move succeeded.

    Defense-in-depth: every API entry already gates input through
    ``_validate_path``, but we re-anchor src/dest against the configured
    media roots here so a future caller cannot bypass the gate and so the
    static analyser sees a visible containment check right before the
    filesystem sinks (``samefile``, ``resolve``, ``_force_delete``).
    """
    try:
        _src_resolved = Path(src_path).resolve(strict=False)
        _dest_resolved = Path(dest_path).resolve(strict=False)
    except (ValueError, OSError, RuntimeError):
        logger.error("[MERGE] Path resolve failed: src=%s dest=%s", src_path, dest_path)
        return {"error": "path_not_allowed"}

    _roots = [r.resolve(strict=False) for r in _media_roots()]
    if not _roots or not all(
        any(p.is_relative_to(root) for root in _roots)
        for p in (_src_resolved, _dest_resolved)
    ):
        logger.error("[MERGE] Containment rejected: src=%s dest=%s", src_path, dest_path)
        return {"error": "path_not_allowed"}

    src  = Path(src_path)
    dest = Path(dest_path)

    if not src.is_dir():
        logger.error("[MERGE] Source is not a directory: %s", src_path)
        return {"error": "source_not_a_directory"}
    if not dest.is_dir():
        logger.error("[MERGE] Destination is not a directory: %s", dest_path)
        return {"error": "destination_not_a_directory"}

    # SAFETY: refuse self-merge — would nuke the source after a no-op loop.
    try:
        if src.samefile(dest):
            logger.error(
                "[MERGE] Self-merge refused: src and dest point to the same inode: %s",
                src_path,
            )
            return {"error": "self_merge_refused"}
    except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
        pass
    if str(src.resolve()) == str(dest.resolve()):
        logger.error(
            "[MERGE] Self-merge refused: resolved paths are identical: %s",
            src_path,
        )
        return {"error": "self_merge_refused"}

    try:
        moved = 0
        failed = 0
        for item in src.iterdir():
            target = dest / item.name
            if target.exists() and item.is_dir() and target.is_dir():
                sub = await _merge_folder_into(str(item), str(target))
                if sub.get("error"):
                    failed += 1
                    logger.error(
                        "[MERGE] sub-merge failed %s → %s: %s",
                        item, target, sub.get("error"),
                    )
                else:
                    moved += sub.get("moved", 0)
            else:
                try:
                    await _fast_move(str(item), str(target))
                    moved += 1
                except Exception as e:
                    failed += 1
                    logger.error("[MERGE] mv failed %s → %s: %s", item, target, e)

        # Delete the source ONLY if everything was moved successfully.
        if failed > 0:
            logger.error(
                "[MERGE] %s failure(s) — source kept: %s", failed, src_path,
            )
            return {"error": "partial_merge_failed", "moved": moved, "failed": failed}

        if src.exists():
            await _force_delete(src)

        logger.info(
            "[MERGE] %s items merged from %s → %s", moved, src_path, dest_path,
        )
        return {"success": True, "moved": moved}

    except Exception:
        logger.exception("[MERGE] Failed: src=%s dest=%s", src_path, dest_path)
        return {"error": "merge_failed"}


async def apply_rename(old_path: str, new_name: str):
    err = _validate_path(old_path)
    if err:
        return {"error": err}

    name_err = _validate_name(new_name)
    if name_err:
        return {"error": name_err}
    new_name = _sanitize_name(new_name)

    src = Path(old_path)
    if not src.exists():
        logger.error("[RENAME] File or directory not found: %s", old_path)
        return {"error": "file_or_directory_not_found"}

    dest = src.parent / new_name

    # SAFETY: never merge/delete when src and dest resolve to the SAME
    # path. Renaming a folder to its own name used to trigger
    # _merge_folder_into(src=dest) which no-op'd then _force_delete()'d
    # the only copy on disk.
    try:
        src_resolved = src.resolve()
        dest_resolved = dest.resolve() if dest.exists() else dest
    except Exception:  # noqa: S110 -- best-effort resolve, fall back to non-resolved paths for the no-op check
        src_resolved, dest_resolved = src, dest

    if str(src_resolved) == str(dest_resolved) and src.name == new_name:
        logger.info("[RENAME] Skipped no-op rename: %s → %s", old_path, new_name)
        return {"success": True, "new_path": old_path, "noop": True}

    try:
        if dest.exists():
            # Even if dest.exists() is true, reject the merge when
            # dest points to the same inode as src.
            try:
                if dest.samefile(src):
                    logger.warning(
                        "[RENAME] Refused self-merge — dest is the same file as src: %s",
                        old_path,
                    )
                    return {"error": f"'{new_name}' refers to the folder itself"}
            except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
                pass

            if src.is_dir() and dest.is_dir():
                merge_result = await _merge_folder_into(str(src), str(dest))
                if merge_result.get("success"):
                    logger.info("[RENAME] Merge succeeded: %s → %s", old_path, dest)
                    return {"success": True, "new_path": str(dest), "merged": True}
                else:
                    return {"error": f"'{new_name}' already exists and the merge failed: {merge_result.get('error')}"}
            else:
                return {"error": f"'{new_name}' already exists"}

        src.rename(dest)
        return {"success": True, "new_path": str(dest)}

    except Exception:
        logger.exception("[RENAME] Failed: old=%s new=%s", old_path, new_name)
        return {"error": "rename_failed"}


async def apply_rename_batch(items: list, cat: str = "") -> list:
    if not items:
        return []

    def make_absolute(path: str, cat: str = "") -> str:
        if path.startswith("/"):
            return path
        if cat and cat in MEDIA_FOLDERS:
            return f"{MEDIA_FOLDERS[cat]}/{path.strip('/')}"
        logger.error("[RENAME] Unable to resolve relative path: %s", path)
        return path

    results = []
    for item in items:
        abs_path = make_absolute(item["old_path"], cat)

        err = _validate_path(abs_path)
        if err:
            results.append({"old_path": item["old_path"], "error": err})
            continue

        name_err = _validate_name(item["new_name"])
        if name_err:
            results.append({"old_path": item["old_path"], "error": name_err})
            continue

        clean_name = _sanitize_name(item["new_name"])
        r = await apply_rename(abs_path, clean_name)
        r["old_path"] = item["old_path"]
        results.append(r)

    return results


def preview_rename(old_path: str, new_name: str):
    parts    = old_path.rsplit("/", 1)
    parent   = parts[0] if len(parts) > 1 else ""
    new_path = f"{parent}/{new_name}"
    return {
        "old_name": old_path.split("/")[-1],
        "new_name": new_name,
        "old_path": old_path,
        "new_path": new_path,
    }
