"""Guard tests pinning the short error code contract on media services.

Cycle 20 replaced nine sites in ``services/tmdb.py``,
``services/media_manager/files.py``, ``api/media/_metadata.py`` and
``api/media/_browse.py`` that previously embedded either ``str(exc)``,
ffprobe stderr or raw filesystem paths into the API response. Without
these tests a future refactor could silently regress to leaking those
details and CodeQL ``py/stack-trace-exposure`` would only catch it via
the nightly scan, not at PR time.

Each test forces the failure path on a specific function (mocking the
external dependency that would normally raise or produce the leak) and
asserts:

1. the returned ``error`` field is the short code,
2. no fragment of the synthetic ``_LEAK_MARKER`` ends up in the response
   payload.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


_LEAK_MARKER = "/secret/path"


# services/tmdb.py


@pytest.fixture
def _tmdb_key(monkeypatch):
    import services.tmdb as tmdb_service

    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    tmdb_service.invalidate_tmdb_key_cache()
    yield
    tmdb_service.invalidate_tmdb_key_cache()


@pytest.mark.asyncio
async def test_search_tmdb_returns_short_code_on_exception(_tmdb_key):
    import services.tmdb as tmdb_service

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} boom"))
    with patch("services.tmdb.get_external_client", return_value=fake_client):
        result = await tmdb_service._search_tmdb("movie", "x")

    assert result == {"error": "tmdb_search_failed"}
    assert _LEAK_MARKER not in str(result)


@pytest.mark.asyncio
async def test_get_tv_seasons_returns_short_code_on_exception(_tmdb_key):
    import services.tmdb as tmdb_service

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} boom"))
    with patch("services.tmdb.get_external_client", return_value=fake_client):
        result = await tmdb_service.get_tv_seasons(1)

    assert result == {"error": "tmdb_seasons_failed"}
    assert _LEAK_MARKER not in str(result)


@pytest.mark.asyncio
async def test_get_season_episodes_returns_short_code_on_exception(_tmdb_key):
    import services.tmdb as tmdb_service

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} boom"))
    with patch("services.tmdb.get_external_client", return_value=fake_client):
        result = await tmdb_service.get_season_episodes(1, 1)

    assert result == {"error": "tmdb_episodes_failed"}
    assert _LEAK_MARKER not in str(result)


@pytest.mark.asyncio
async def test_get_media_detail_returns_short_code_on_exception(_tmdb_key):
    import services.tmdb as tmdb_service

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} boom"))
    with patch("services.tmdb.get_external_client", return_value=fake_client):
        result = await tmdb_service.get_media_detail("movie", 1)

    assert result == {"error": "tmdb_detail_failed"}
    assert _LEAK_MARKER not in str(result)


# services/media_manager/files.py


@pytest.mark.asyncio
async def test_list_files_unknown_folder_returns_short_code():
    from services.media_manager.files import list_files

    result = await list_files("nonexistent_folder_xyz")

    assert result == {"error": "unknown_folder"}


@pytest.mark.asyncio
async def test_list_files_permission_denied_returns_short_code(monkeypatch, tmp_path):
    from services.media_manager import files as files_module

    media_dir = tmp_path / "movies"
    media_dir.mkdir()

    monkeypatch.setattr(files_module, "MEDIA_FOLDERS", {"movies": str(media_dir)})
    monkeypatch.setattr(files_module, "_validate_path", lambda _path: None)

    def _raise_permission(self, *args, **kwargs):
        raise PermissionError(f"{_LEAK_MARKER} permission boom")

    monkeypatch.setattr(Path, "iterdir", _raise_permission)

    result = await files_module.list_files("movies")

    assert result == {"error": "permission_denied"}
    assert _LEAK_MARKER not in str(result)


@pytest.mark.asyncio
async def test_list_files_generic_failure_returns_short_code(monkeypatch, tmp_path):
    from services.media_manager import files as files_module

    media_dir = tmp_path / "movies"
    media_dir.mkdir()

    monkeypatch.setattr(files_module, "MEDIA_FOLDERS", {"movies": str(media_dir)})
    monkeypatch.setattr(files_module, "_validate_path", lambda _path: None)

    def _raise_generic(self, *args, **kwargs):
        raise RuntimeError(f"{_LEAK_MARKER} generic boom")

    monkeypatch.setattr(Path, "iterdir", _raise_generic)

    result = await files_module.list_files("movies")

    assert result == {"error": "list_failed"}
    assert _LEAK_MARKER not in str(result)


# api/media/_metadata.py — _run_ffprobe


class _FakeProc:
    """Minimal stand-in for asyncio.subprocess.Process."""

    def __init__(self, stdout: bytes, stderr: bytes):
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return self._stdout, self._stderr


@pytest.mark.asyncio
async def test_run_ffprobe_empty_output_returns_short_code(monkeypatch):
    from api.media import _metadata

    async def _fake_create(*_args, **_kwargs):
        return _FakeProc(stdout=b"", stderr=f"{_LEAK_MARKER} ffprobe boom".encode())

    monkeypatch.setattr(_metadata.asyncio, "create_subprocess_exec", _fake_create)

    data, err = await _metadata._run_ffprobe("/fake/path.mkv")

    assert data is None
    assert err == "ffprobe_empty_output"
    assert _LEAK_MARKER not in str((data, err))


@pytest.mark.asyncio
async def test_run_ffprobe_timeout_returns_short_code(monkeypatch):
    from api.media import _metadata

    async def _fake_create(*_args, **_kwargs):
        return _FakeProc(stdout=b"{}", stderr=b"")

    async def _raise_timeout(coro, *_args, **_kwargs):
        # Close the pending coroutine to avoid a RuntimeWarning about
        # never-awaited coroutines when wait_for short-circuits.
        coro.close()
        raise asyncio.TimeoutError()

    monkeypatch.setattr(_metadata.asyncio, "create_subprocess_exec", _fake_create)
    monkeypatch.setattr(_metadata.asyncio, "wait_for", _raise_timeout)

    data, err = await _metadata._run_ffprobe("/fake/path.mkv")

    assert data is None
    assert err == "ffprobe_timeout"


@pytest.mark.asyncio
async def test_run_ffprobe_json_parse_returns_short_code(monkeypatch):
    from api.media import _metadata

    async def _fake_create(*_args, **_kwargs):
        return _FakeProc(stdout=b"not valid json", stderr=b"")

    monkeypatch.setattr(_metadata.asyncio, "create_subprocess_exec", _fake_create)

    data, err = await _metadata._run_ffprobe("/fake/path.mkv")

    assert data is None
    assert err == "ffprobe_json_parse_failed"


@pytest.mark.asyncio
async def test_run_ffprobe_generic_failure_returns_short_code(monkeypatch):
    from api.media import _metadata

    async def _raise_generic(*_args, **_kwargs):
        raise RuntimeError(f"{_LEAK_MARKER} create boom")

    monkeypatch.setattr(_metadata.asyncio, "create_subprocess_exec", _raise_generic)

    data, err = await _metadata._run_ffprobe("/fake/path.mkv")

    assert data is None
    assert err == "ffprobe_failed"
    assert _LEAK_MARKER not in str((data, err))


# api/media/_browse.py — get_rootpath


@pytest.mark.asyncio
async def test_get_rootpath_unknown_category_returns_short_code():
    from api.media._browse import get_rootpath

    fake_user = MagicMock()
    result = await get_rootpath("nonexistent_xyz", _=fake_user)

    assert result == {"error": "unknown_category"}


# api/media/_metadata.py — get_file_metadata


@pytest.mark.asyncio
async def test_get_file_metadata_path_not_allowed_returns_short_code(monkeypatch):
    from api.media import _metadata

    monkeypatch.setattr(_metadata, "_validate_path", lambda _path: "path_not_allowed")

    fake_user = MagicMock()
    leaky_path = f"{_LEAK_MARKER}/movie.mkv"
    result = await _metadata.get_file_metadata(leaky_path, _=fake_user)

    assert result == {"error": "path_not_allowed"}
    assert _LEAK_MARKER not in str(result)
