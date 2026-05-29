"""Directory deletion goes through ``shutil.rmtree(onexc=...)``.

Guards the migration from the deprecated ``onerror=`` callback (slated for
removal in a future CPython) to ``onexc=`` in
``services.media_manager._io._sync_delete``: a non-empty directory under a
media root must be fully removed via the public ``delete_file`` entry point.
"""
from __future__ import annotations

import pytest

from services import media_manager
from tests._media_helpers import single_media_root


@pytest.mark.asyncio
async def test_delete_file_removes_non_empty_directory_tree(monkeypatch, tmp_path):
    """A non-empty directory under a media root is recursively removed
    (exercises the ``rmtree(onexc=...)`` branch of ``_sync_delete``)."""
    media_root = single_media_root(monkeypatch, tmp_path)
    folder = media_root / "Season 01"
    (folder / "sub").mkdir(parents=True)
    (folder / "ep01.mkv").write_bytes(b"video")
    (folder / "sub" / "ep02.mkv").write_bytes(b"video")

    result = await media_manager.delete_file(str(folder))

    assert result.get("success") is True
    assert not folder.exists()
