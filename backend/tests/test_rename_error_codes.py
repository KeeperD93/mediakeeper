"""Stack-trace exposure regression guards for media-manager rename ops.

Covers CodeQL ``py/stack-trace-exposure`` (#163 / #164) where the broad
``except Exception`` in :func:`_merge_folder_into` and :func:`apply_rename`
used to ``return {"error": str(e)}`` — leaking internal exception messages
(filesystem paths, permission details, OS error codes) all the way to the
API response via the ``apply_rename`` f-string at ``rename.py:134``.

These tests force the outer broad-except path and assert the response is
a stable generic code, with **no** trace of the internal exception text.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from services.media_manager import rename as rename_mod
from services.media_manager.rename import _merge_folder_into, apply_rename


_LEAK_SENTINEL = "INTERNAL_LEAK_SENTINEL_xyz9876_secret_path"


def _make_workspace_tmp(prefix: str) -> Path:
    root = Path(__file__).resolve().parent / prefix / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.mark.asyncio
async def test_merge_folder_into_broad_except_returns_generic_code(monkeypatch):
    """``_merge_folder_into`` outer broad-except must return a stable code,
    never ``str(e)``. CodeQL #163/#164 regression guard."""
    workspace = _make_workspace_tmp("_attack_merge_codes")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        src = media_root / "src_dir"
        dest = media_root / "dest_dir"
        src.mkdir()
        dest.mkdir()
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        from services.media_manager import categories as cat_mod
        monkeypatch.setattr(cat_mod, "MEDIA_FOLDERS", {"movies": str(media_root)})

        async def boom_delete(_path):
            raise OSError(_LEAK_SENTINEL)

        monkeypatch.setattr(rename_mod, "_force_delete", boom_delete)

        result = await _merge_folder_into(str(src), str(dest))

        assert result == {"error": "merge_failed"}
        assert _LEAK_SENTINEL not in str(result)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_apply_rename_broad_except_returns_generic_code(monkeypatch):
    """``apply_rename`` outer broad-except must return a stable code,
    never ``str(e)``. CodeQL #163/#164 regression guard."""
    workspace = _make_workspace_tmp("_attack_rename_codes")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        src_file = media_root / "old.mkv"
        src_file.write_bytes(b"video")
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        from services.media_manager import categories as cat_mod
        monkeypatch.setattr(cat_mod, "MEDIA_FOLDERS", {"movies": str(media_root)})

        def boom_rename(self, _target):
            raise OSError(_LEAK_SENTINEL)

        monkeypatch.setattr(Path, "rename", boom_rename)

        result = await apply_rename(str(src_file), "new.mkv")

        assert result == {"error": "rename_failed"}
        assert _LEAK_SENTINEL not in str(result)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_merge_chain_error_does_not_leak_inner_str_exception(monkeypatch):
    """End-to-end: when ``apply_rename`` delegates to ``_merge_folder_into``
    which hits its broad except, the f-string at ``rename.py:134`` that
    embeds ``merge_result.get('error')`` MUST now embed a generic code,
    not the raw exception text. Direct guard against the f-string sink."""
    workspace = _make_workspace_tmp("_attack_merge_chain")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        src_dir = media_root / "src_dir"
        dest_dir = media_root / "dest_dir"
        src_dir.mkdir()
        dest_dir.mkdir()
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        from services.media_manager import categories as cat_mod
        monkeypatch.setattr(cat_mod, "MEDIA_FOLDERS", {"movies": str(media_root)})

        async def boom_delete(_path):
            raise OSError(_LEAK_SENTINEL)

        monkeypatch.setattr(rename_mod, "_force_delete", boom_delete)

        # apply_rename("media/src_dir", "dest_dir") → dest exists → merge path
        result = await apply_rename(str(src_dir), "dest_dir")

        assert result.get("error") is not None
        assert _LEAK_SENTINEL not in str(result)
        assert "merge_failed" in str(result.get("error", ""))
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_merge_source_not_dir_returns_generic_code(monkeypatch):
    """When src is a file (not a directory), the response code must be a
    stable string with no filesystem path embedded."""
    workspace = _make_workspace_tmp("_attack_leak_paths")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        src_file = media_root / "not_a_dir.mkv"
        src_file.write_bytes(b"video")
        dest_dir = media_root / "dest_dir"
        dest_dir.mkdir()
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        from services.media_manager.rename import _merge_folder_into

        result = await _merge_folder_into(str(src_file), str(dest_dir))

        assert result == {"error": "source_not_a_directory"}
        assert str(src_file) not in str(result)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_merge_dest_not_dir_returns_generic_code(monkeypatch):
    """When dest is a file (not a directory), the response code must be a
    stable string with no filesystem path embedded."""
    workspace = _make_workspace_tmp("_attack_leak_paths")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        src_dir = media_root / "src_dir"
        src_dir.mkdir()
        dest_file = media_root / "not_a_dir.mkv"
        dest_file.write_bytes(b"video")
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        from services.media_manager.rename import _merge_folder_into

        result = await _merge_folder_into(str(src_dir), str(dest_file))

        assert result == {"error": "destination_not_a_directory"}
        assert str(dest_file) not in str(result)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.asyncio
async def test_apply_rename_missing_path_returns_generic_code(monkeypatch):
    """When the source path passes ``_validate_path`` (parent exists in
    ``MEDIAKEEPER_PATH_ROOTS``) but the file itself is missing, the
    response must be a stable code with no path leak."""
    workspace = _make_workspace_tmp("_attack_leak_paths")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        missing = media_root / "does_not_exist.mkv"
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        from services.media_manager import categories as cat_mod
        monkeypatch.setattr(cat_mod, "MEDIA_FOLDERS", {"movies": str(media_root)})

        result = await apply_rename(str(missing), "new.mkv")

        assert result == {"error": "file_or_directory_not_found"}
        assert str(missing) not in str(result)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
