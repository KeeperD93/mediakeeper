"""Pre-network guards for download_subtitle (allowed zones, extension)."""
import shutil
from unittest.mock import AsyncMock, patch

import pytest

from core.security import create_access_token
from services import opensubtitles

from _subtitle_fakes import _make_workspace_tmp


@pytest.mark.asyncio
async def test_download_subtitle_rejects_destination_outside_roots_before_network(monkeypatch):
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        outside_dir = root / "outside"
        outside_dir.mkdir()
        destination = outside_dir / "movie.fr.srt"

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        async def fake_headers(_db):
            return {"Api-Key": "test"}

        monkeypatch.setattr(opensubtitles.auth, "_get_headers", fake_headers)
        monkeypatch.setattr(
            opensubtitles.search,
            "get_external_client",
            lambda: pytest.fail("No network call should be made"),
        )

        result = await opensubtitles.download_subtitle(None, 123, str(destination))

        assert result["error"] == "path_outside_configured_zones"
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_download_subtitle_rejects_invalid_extension_before_network(monkeypatch):
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        destination = media_root / "movie.txt"

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        async def fake_headers(_db):
            return {"Api-Key": "test"}

        monkeypatch.setattr(opensubtitles.auth, "_get_headers", fake_headers)
        monkeypatch.setattr(
            opensubtitles.search,
            "get_external_client",
            lambda: pytest.fail("No network call should be made"),
        )

        result = await opensubtitles.download_subtitle(None, 123, str(destination))

        assert result["error"] == "File type not allowed"
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_subtitle_search_rejects_file_path_outside_roots_before_hash(
    monkeypatch, client, admin_user, workspace_tmp_path,
):
    media_root = workspace_tmp_path / "media"
    media_root.mkdir()
    outside_dir = workspace_tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "movie.mkv"
    outside_file.write_bytes(b"0" * 70000)

    monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username}))

    with patch(
        "api.subtitles._search.search_subtitles",
        new=AsyncMock(side_effect=AssertionError("search_subtitles should not run")),
    ):
        resp = await client.post("/api/subtitles/search", json={
            "query": "movie",
            "file_path": str(outside_file),
        })

    assert resp.status_code == 400
    assert resp.json()["detail"] == "path_outside_configured_zones"
