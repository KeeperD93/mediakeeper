"""Renaming of files/folders + merge of same-named folders."""
import asyncio
import logging
from pathlib import Path

from ._io import _fast_move, _force_delete
from ._paths import (
    _ensure_within_media_roots,
    _sanitize_name,
    _validate_name,
    _validate_path,
)
from .categories import MEDIA_FOLDERS

logger = logging.getLogger("mediakeeper.media_manager")

# Serialise rename mutations: the dest-existence check and the os-level rename
# must be atomic relative to each other, otherwise two concurrent renames
# targeting the same destination could race between the check and the rename
# (TOCTOU, CWE-367) and silently overwrite. Renames are admin-only and rare,
# so a single global lock is simpler and safer than a per-directory registry.
_rename_lock = asyncio.Lock()


async def _merge_folder_into(src_path: str, dest_path: str) -> dict:
    """Merge src into dest, then delete src — only if every move succeeded.

    Defense-in-depth: ``_ensure_within_media_roots`` validates and returns
    the resolved ``Path`` for both src and dest. All downstream filesystem
    sinks (``is_dir``, ``samefile``, ``iterdir``, ``_force_delete``, etc.)
    operate on the *returned* ``Path`` rather than on a freshly-built
    ``Path(input_string)``. The taint flow from the user-controlled string
    is therefore broken at the function boundary via ``os.path.realpath`` +
    prefix containment, which CodeQL recognises as a barrier guard for
    ``py/path-injection``.
    """
    src = _ensure_within_media_roots(src_path)
    dest = _ensure_within_media_roots(dest_path)
    if src is None or dest is None:
        logger.error("[MERGE] Containment rejected: src=%s dest=%s", src_path, dest_path)
        return {"error": "path_not_allowed"}

    if not src.is_dir():
        logger.error("[MERGE] Source is not a directory: %s", src_path)
        return {"error": "source_not_a_directory"}
    if not dest.is_dir():
        logger.error("[MERGE] Destination is not a directory: %s", dest_path)
        return {"error": "destination_not_a_directory"}

    # SAFETY: refuse self-merge — would nuke the source after a no-op loop.
    # src and dest are already resolved by _ensure_within_media_roots,
    # so the equality check is a direct comparison; samefile() is the
    # cross-filesystem fallback (handles hardlinks pointing to the same
    # inode despite different paths).
    if src == dest:
        logger.error(
            "[MERGE] Self-merge refused: resolved paths are identical: %s",
            src_path,
        )
        return {"error": "self_merge_refused"}
    try:
        if src.samefile(dest):
            logger.error(
                "[MERGE] Self-merge refused: src and dest point to the same inode: %s",
                src_path,
            )
            return {"error": "self_merge_refused"}
    except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
        pass

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


async def apply_rename(old_path: str, new_name: str) -> dict:
    src = _ensure_within_media_roots(old_path)
    if src is None:
        logger.error("[RENAME] Containment rejected: old=%s", old_path)
        return {"error": "path_not_allowed"}

    name_err = _validate_name(new_name)
    if name_err:
        return {"error": name_err}
    new_name = _sanitize_name(new_name)
    # Re-validate after sanitisation: a name of only strippable chars ("<>",
    # "***", ",") collapses to "" (or "..," to ".."), making dest == src.parent
    # and silently merging+deleting the folder into its parent. Fail closed.
    name_err = _validate_name(new_name)
    if name_err:
        logger.warning("[RENAME] Name rejected after sanitisation: old=%s", old_path)
        return {"error": name_err}

    if not src.exists():
        logger.error("[RENAME] File or directory not found: %s", old_path)
        return {"error": "file_or_directory_not_found"}

    # ``dest`` is built from ``src`` (already sanitised by the helper) and
    # ``new_name`` (validated by ``_validate_name`` + sanitised by
    # ``_sanitize_name``). Re-confine it against the roots: ``src`` may itself
    # be a configured media root, so ``src.parent`` legitimately escapes one
    # level above the zone — renaming a root would otherwise relocate the whole
    # root outside the configured paths. Feeding ``dest`` back through the
    # realpath+prefix barrier fails closed on any out-of-root target.
    dest = _ensure_within_media_roots(str(src.parent / new_name))
    if dest is None:
        logger.error("[RENAME] Containment rejected dest: old=%s new=%s", old_path, new_name)
        return {"error": "path_not_allowed"}

    # SAFETY: never merge/delete when src and dest resolve to the SAME
    # path. Renaming a folder to its own name used to trigger
    # _merge_folder_into(src=dest) which no-op'd then _force_delete()'d
    # the only copy on disk.
    try:
        dest_resolved = dest.resolve() if dest.exists() else dest
    except Exception:  # noqa: S110 -- best-effort resolve, fall back to non-resolved dest for the no-op check
        dest_resolved = dest

    if src == dest_resolved and src.name == new_name:
        logger.info("[RENAME] Skipped no-op rename: %s → %s", old_path, new_name)
        return {"success": True, "new_path": old_path, "noop": True}

    try:
        async with _rename_lock:
            if dest.exists():
                # Even if dest.exists() is true, reject the merge when
                # dest points to the same inode as src.
                try:
                    if dest.samefile(src):
                        logger.warning(
                            "[RENAME] Refused self-merge — dest is the same file as src: %s",
                            old_path,
                        )
                        return {"error": "self_merge_refused"}
                except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
                    pass

                if src.is_dir() and dest.is_dir():
                    merge_result = await _merge_folder_into(str(src), str(dest))
                    if merge_result.get("success"):
                        logger.info("[RENAME] Merge succeeded: %s → %s", old_path, dest)
                        return {"success": True, "new_path": str(dest), "merged": True}
                    else:
                        logger.error(
                            "[RENAME] Destination exists, merge failed: old=%s new=%s sub_error=%s",
                            old_path, new_name, merge_result.get("error"),
                        )
                        return {"error": "destination_exists_merge_failed", "merge_error": merge_result.get("error")}
                else:
                    logger.warning("[RENAME] Destination exists: old=%s new=%s", old_path, new_name)
                    return {"error": "destination_exists"}

            await asyncio.to_thread(src.rename, dest)
            return {"success": True, "new_path": str(dest)}

    except Exception:
        logger.exception("[RENAME] Failed: old=%s new=%s", old_path, new_name)
        return {"error": "rename_failed"}


async def apply_rename_batch(items: list[dict], cat: str = "") -> list[dict]:
    if not items:
        return []

    def make_absolute(path: str, cat: str = "") -> str:
        if path.startswith("/"):
            return path
        if cat and cat in MEDIA_FOLDERS:
            return str(Path(MEDIA_FOLDERS[cat]) / path.strip("/\\"))
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


def preview_rename(old_path: str, new_name: str) -> dict:
    """Format-only preview of the rename target.

    INTENTIONALLY performs no path/name validation: this is a pure display
    helper that never touches the filesystem. ``apply_rename`` revalidates
    (``_validate_name`` + ``_sanitize_name`` + containment) before any real
    operation, so a preview may legitimately show a target the rename would
    later reject.
    """
    parts    = old_path.rsplit("/", 1)
    parent   = parts[0] if len(parts) > 1 else ""
    new_path = f"{parent}/{new_name}"
    return {
        "old_name": old_path.split("/")[-1],
        "new_name": new_name,
        "old_path": old_path,
        "new_path": new_path,
    }
