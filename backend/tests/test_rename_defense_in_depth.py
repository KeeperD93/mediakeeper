"""Defense-in-depth containment guards inside ``_merge_folder_into``.

Even though every API entry point already validates inputs via
``_validate_path``, ``_merge_folder_into`` re-anchors src/dest against the
configured media roots immediately before the filesystem sinks
(``samefile``, ``resolve``, ``_force_delete``).

These tests pin that second gate so a future refactor cannot drop it
silently, and so the CodeQL ``py/path-injection`` regression coverage
stays explicit (alerts #165-#170).
"""
from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest

from services.media_manager.rename import _merge_folder_into, apply_rename


def _make_workspace_tmp(prefix: str) -> Path:
    root = Path(__file__).resolve().parent / prefix / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.mark.asyncio
async def test_merge_rejects_src_outside_media_roots(monkeypatch):
    """A src path outside every configured root must be refused before
    any filesystem operation touches it."""
    workspace = _make_workspace_tmp("_attack_merge_containment")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        outside = workspace / "outside"
        outside.mkdir()
        dest_dir = media_root / "dest_dir"
        dest_dir.mkdir()
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        result = await _merge_folder_into(str(outside), str(dest_dir))

        assert result == {"error": "path_not_allowed"}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_merge_rejects_dest_outside_media_roots(monkeypatch):
    """A dest path outside every configured root must be refused even when
    the src is legitimate (defence against an attacker forging the
    destination)."""
    workspace = _make_workspace_tmp("_attack_merge_containment")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        src_dir = media_root / "src_dir"
        src_dir.mkdir()
        outside_dest = workspace / "outside_dest"
        outside_dest.mkdir()
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        result = await _merge_folder_into(str(src_dir), str(outside_dest))

        assert result == {"error": "path_not_allowed"}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_merge_rejects_parent_traversal_payload(monkeypatch):
    """A `..` payload that resolves outside the roots must be refused
    even though the literal string starts inside a root."""
    workspace = _make_workspace_tmp("_attack_merge_containment")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        sibling = workspace / "sibling"
        sibling.mkdir()
        dest_dir = media_root / "dest_dir"
        dest_dir.mkdir()
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        attack_src = f"{media_root}/sub/../../sibling"
        result = await _merge_folder_into(attack_src, str(dest_dir))

        assert result == {"error": "path_not_allowed"}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_merge_accepts_paths_inside_media_root(monkeypatch):
    """The containment gate must not break legitimate operations: paths
    living under a configured root pass through to the merge logic."""
    workspace = _make_workspace_tmp("_attack_merge_containment")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        src_dir = media_root / "src_dir"
        dest_dir = media_root / "dest_dir"
        src_dir.mkdir()
        dest_dir.mkdir()
        (src_dir / "movie.mkv").write_bytes(b"video")
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        result = await _merge_folder_into(str(src_dir), str(dest_dir))

        # Either succeeded with `moved>0`, or fell into the legit business
        # logic — never the containment refusal.
        assert result.get("error") != "path_not_allowed"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_merge_accepts_nested_subpath(monkeypatch):
    """Recursive calls operate on sub-paths inside a validated root. The
    containment gate must not reject those legitimate nested paths."""
    workspace = _make_workspace_tmp("_attack_merge_containment")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        nested_src = media_root / "series" / "season1"
        nested_dest = media_root / "series" / "season2"
        nested_src.mkdir(parents=True)
        nested_dest.mkdir(parents=True)
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        result = await _merge_folder_into(str(nested_src), str(nested_dest))

        assert result.get("error") != "path_not_allowed"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_merge_rejects_absolute_path_outside_roots(monkeypatch):
    """Absolute paths that bypass MEDIA_FOLDERS (typical attacker payload
    targeting /etc/passwd or C:\\Windows) must be refused at the gate."""
    workspace = _make_workspace_tmp("_attack_merge_containment")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        dest_dir = media_root / "dest_dir"
        dest_dir.mkdir()
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        attack = "/etc/passwd" if sys.platform != "win32" else "C:\\Windows\\System32"
        result = await _merge_folder_into(attack, str(dest_dir))

        assert result == {"error": "path_not_allowed"}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_rename_rejects_name_that_sanitises_to_empty(monkeypatch):
    """A new_name made only of strippable characters passes the pre-sanitise
    validator but collapses to "" (or "..," to "..") afterwards — which would
    make dest == src.parent and silently merge+delete the folder into its
    parent. ``apply_rename`` must re-validate after sanitisation and refuse,
    leaving the source folder, its contents and the homonym sibling intact."""
    workspace = _make_workspace_tmp("_attack_rename_empty")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        collection = media_root / "MaCollection"
        collection.mkdir()
        (collection / "movie.mkv").write_bytes(b"video")
        sibling = media_root / "movie.mkv"  # homonym sibling in the parent
        sibling.write_bytes(b"sibling")
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        for payload in ("<>", "***", "???", "|||", ",", "..,", "...", ". ."):
            result = await apply_rename(str(collection), payload)
            assert result.get("error") in {"empty_name", "name_not_allowed"}, payload

        assert collection.is_dir()
        assert (collection / "movie.mkv").read_bytes() == b"video"
        assert sibling.read_bytes() == b"sibling"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_rename_rejects_renaming_a_configured_root(monkeypatch):
    """Renaming a configured media root would resolve ``dest`` to
    ``root.parent / new_name`` — one level ABOVE the zone — and relocate the
    whole root out of the configured paths (the containment helper accepts a
    path equal to a root, so ``src.parent`` legitimately escapes). ``apply_rename``
    must re-confine ``dest`` and refuse, leaving the root and its contents intact."""
    workspace = _make_workspace_tmp("_attack_rename_root")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        (media_root / "movie.mkv").write_bytes(b"video")
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        result = await apply_rename(str(media_root), "PWNED_OUTSIDE_ROOT")

        assert result == {"error": "path_not_allowed"}
        # The root must NOT have been relocated to workspace/PWNED_OUTSIDE_ROOT.
        assert media_root.is_dir()
        assert (media_root / "movie.mkv").read_bytes() == b"video"
        assert not (workspace / "PWNED_OUTSIDE_ROOT").exists()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_rename_accepts_legit_rename_inside_root(monkeypatch):
    """The dest re-confinement must not break a normal rename: a folder inside
    a root renamed to another in-root name still succeeds with its contents."""
    workspace = _make_workspace_tmp("_rename_legit")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        folder = media_root / "OldName"
        folder.mkdir()
        (folder / "movie.mkv").write_bytes(b"video")
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        result = await apply_rename(str(folder), "NewName")

        assert result.get("error") is None
        assert (media_root / "NewName").is_dir()
        assert (media_root / "NewName" / "movie.mkv").read_bytes() == b"video"
        assert not folder.exists()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
