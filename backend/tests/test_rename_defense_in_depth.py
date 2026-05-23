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

from services.media_manager.rename import _merge_folder_into


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

        from services.media_manager import categories as cat_mod
        monkeypatch.setattr(cat_mod, "MEDIA_FOLDERS", {"movies": str(media_root)})

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

        from services.media_manager import categories as cat_mod
        monkeypatch.setattr(cat_mod, "MEDIA_FOLDERS", {"movies": str(media_root)})

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

        from services.media_manager import categories as cat_mod
        monkeypatch.setattr(cat_mod, "MEDIA_FOLDERS", {"movies": str(media_root)})

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

        from services.media_manager import categories as cat_mod
        monkeypatch.setattr(cat_mod, "MEDIA_FOLDERS", {"movies": str(media_root)})

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

        from services.media_manager import categories as cat_mod
        monkeypatch.setattr(cat_mod, "MEDIA_FOLDERS", {"movies": str(media_root)})

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

        from services.media_manager import categories as cat_mod
        monkeypatch.setattr(cat_mod, "MEDIA_FOLDERS", {"movies": str(media_root)})

        attack = "/etc/passwd" if sys.platform != "win32" else "C:\\Windows\\System32"
        result = await _merge_folder_into(attack, str(dest_dir))

        assert result == {"error": "path_not_allowed"}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
