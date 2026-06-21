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
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

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


@pytest.mark.asyncio
async def test_download_subtitle_aborts_when_body_exceeds_cap(monkeypatch):
    """A subtitle body larger than MAX_SUBTITLE_BYTES is refused mid-stream
    and never written to disk (#402)."""
    from types import SimpleNamespace

    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        destination = media_root / "movie.fr.srt"
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))
        monkeypatch.setattr(opensubtitles.search, "MAX_SUBTITLE_BYTES", 10)

        async def fake_headers(_db):
            return {"Api-Key": "test"}

        async def _oversized():
            yield b"x" * 50  # one chunk already over the 10-byte cap

        class _StreamCtx:
            async def __aenter__(self):
                return SimpleNamespace(status_code=200, aiter_bytes=_oversized)

            async def __aexit__(self, *exc):
                return False

        class _FakeClient:
            async def post(self, *a, **k):
                return SimpleNamespace(
                    status_code=200, json=lambda: {"link": "http://os.test/dl"},
                )

            def stream(self, *a, **k):
                return _StreamCtx()

        monkeypatch.setattr(opensubtitles.auth, "_get_headers", fake_headers)
        monkeypatch.setattr(opensubtitles.search, "get_external_client", lambda: _FakeClient())

        result = await opensubtitles.download_subtitle(None, 123, str(destination))

        assert result["error"] == "subtitle_too_large"
        assert not destination.exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_download_subtitle_writes_file_and_reports_size(monkeypatch):
    """A sub-cap download writes the file and returns success with the right
    size — guards the streamed-read size accounting (#402): the size must come
    from the accumulated buffer, not the closed streaming response."""
    from types import SimpleNamespace

    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        destination = media_root / "movie.fr.srt"
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        body = b"1\n00:00:01,000 --> 00:00:02,000\nHello\n"

        async def fake_headers(_db):
            return {"Api-Key": "test"}

        async def _chunks():
            yield body

        class _StreamCtx:
            async def __aenter__(self):
                return SimpleNamespace(status_code=200, aiter_bytes=_chunks)

            async def __aexit__(self, *exc):
                return False

        class _FakeClient:
            async def post(self, *a, **k):
                return SimpleNamespace(
                    status_code=200, json=lambda: {"link": "http://os.test/dl"},
                )

            def stream(self, *a, **k):
                return _StreamCtx()

        monkeypatch.setattr(opensubtitles.auth, "_get_headers", fake_headers)
        monkeypatch.setattr(opensubtitles.search, "get_external_client", lambda: _FakeClient())
        monkeypatch.setattr("services.subtitle_tools.fix_encoding", lambda *a, **k: {"changed": False})

        result = await opensubtitles.download_subtitle(None, 123, str(destination))

        assert result.get("success") is True, result
        assert result["size"] == len(body)
        assert destination.read_bytes() == body
    finally:
        shutil.rmtree(root, ignore_errors=True)
