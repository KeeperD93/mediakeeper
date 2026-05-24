"""Guard tests pinning the short error code contract on subtitle services.

Cycle 19 replaced seven ``except Exception as e: return {"error":
str(e)[:200]}`` sites in services/opensubtitles/* and
services/subtitle_tools/* with short stable identifiers. Without these
tests a future refactor could silently regress to leaking ``str(exc)``
into the HTTP response body, and CodeQL ``py/stack-trace-exposure``
would only catch it via the nightly scan, not at PR time.

Each test forces the failure path on a specific service (mocking the
external dependency that would normally raise) and asserts:

1. the returned ``error`` field is the short code,
2. no fragment of the synthetic exception message (intentionally
   crafted to include a fake path like ``/secret/path``) ends up in
   the response payload.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


_LEAK_MARKER = "/secret/path"


# services/opensubtitles/search.py — search_subtitles


@pytest.mark.asyncio
async def test_search_subtitles_returns_short_code_on_exception(monkeypatch):
    from services.opensubtitles import search as search_module

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} leak"))
    monkeypatch.setattr(search_module, "get_external_client", lambda: fake_client)
    monkeypatch.setattr(
        search_module.auth,
        "_get_headers",
        AsyncMock(return_value={"Api-Key": "k"}),
    )

    result = await search_module.search_subtitles(db=None, query="x")

    assert result == {"error": "search_failed", "results": []}
    assert _LEAK_MARKER not in str(result)


# services/opensubtitles/search.py — download_subtitle


@pytest.mark.asyncio
async def test_download_subtitle_returns_short_code_on_exception(monkeypatch, tmp_path):
    from services.opensubtitles import search as search_module

    fake_client = AsyncMock()
    fake_client.post = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} leak"))
    monkeypatch.setattr(search_module, "get_external_client", lambda: fake_client)
    monkeypatch.setattr(
        search_module.auth,
        "_get_headers",
        AsyncMock(return_value={"Api-Key": "k"}),
    )

    dest = str(tmp_path / "sub.srt")
    result = await search_module.download_subtitle(
        db=None, file_id=1, destination_path=dest, allow_any_path=True,
    )

    assert result == {"error": "download_failed"}
    assert _LEAK_MARKER not in str(result)


# services/opensubtitles/search.py — get_quota


@pytest.mark.asyncio
async def test_get_quota_returns_short_code_on_exception(monkeypatch):
    from services.opensubtitles import search as search_module

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} leak"))
    monkeypatch.setattr(search_module, "get_external_client", lambda: fake_client)
    monkeypatch.setattr(
        search_module.auth,
        "_get_headers",
        AsyncMock(return_value={"Api-Key": "k"}),
    )

    result = await search_module.get_quota(db=None)

    assert result == {"error": "quota_failed"}
    assert _LEAK_MARKER not in str(result)


# services/opensubtitles/remove.py — _resolve_remove_target


@pytest.mark.asyncio
async def test_resolve_remove_target_returns_short_code_on_exception(monkeypatch):
    from services.opensubtitles import remove as remove_module

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} leak"))
    monkeypatch.setattr(remove_module, "get_internal_client", lambda: fake_client)

    with patch(
        "services.emby._get_emby_config",
        new=AsyncMock(return_value=("http://emby", "key")),
    ):
        ctx, err = await remove_module._resolve_remove_target(
            db=None, item_id="123", require_single=0,
        )

    assert ctx == {}
    assert err == {"error": "resolve_target_failed"}
    assert _LEAK_MARKER not in str(err)


# services/opensubtitles/paths.py — delete_external_subtitle


def test_delete_external_subtitle_returns_short_code_on_exception(tmp_path):
    from services.opensubtitles.paths import delete_external_subtitle

    # File does not exist -> p.unlink() raises FileNotFoundError, caught
    # by the broad except and mapped to the short code.
    missing = tmp_path / "ghost.srt"

    result = delete_external_subtitle(str(missing), allow_any_path=True)

    assert result == {"error": "delete_failed"}
    assert str(missing) not in str(result)


# services/subtitle_tools/encoding.py — fix_encoding


def test_fix_encoding_returns_short_code_on_exception(monkeypatch, tmp_path):
    from services.subtitle_tools import encoding as encoding_module

    subtitle = tmp_path / "movie.fr.srt"
    subtitle.write_bytes(b"random bytes")

    def _raise_detect(_raw):
        raise RuntimeError(f"{_LEAK_MARKER} chardet boom")

    monkeypatch.setattr(encoding_module.chardet, "detect", _raise_detect)

    result = encoding_module.fix_encoding(str(subtitle), allow_any_path=True)

    assert result["error"] == "encoding_failed"
    assert result["converted"] is False
    assert _LEAK_MARKER not in str(result)


# services/subtitle_tools/shift.py — shift_srt


def test_shift_srt_returns_short_code_on_exception(monkeypatch, tmp_path):
    from services.subtitle_tools import shift as shift_module

    subtitle = tmp_path / "movie.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nHi\n", encoding="utf-8",
    )

    def _raise_detect(_raw):
        raise RuntimeError(f"{_LEAK_MARKER} chardet boom")

    monkeypatch.setattr(shift_module.chardet, "detect", _raise_detect)

    result = shift_module.shift_srt(
        str(subtitle), offset_ms=1000, allow_any_path=True,
    )

    assert result == {"error": "shift_failed"}
    assert _LEAK_MARKER not in str(result)


# services/opensubtitles/_remux.py — _safe_remux ffmpeg failure


@pytest.mark.asyncio
async def test_safe_remux_returns_short_code_on_ffmpeg_failure(monkeypatch, tmp_path):
    """FFmpeg returns rc != 0 with stderr embedding a path-like leak: the
    short ``ffmpeg_failed`` code must reach the caller, the stderr stays
    server-side via ``logger.error``."""
    from services.opensubtitles import _remux

    source = tmp_path / "movie.mkv"
    source.write_bytes(b"fake bytes")

    leaky_stderr = f"ffmpeg cannot open {_LEAK_MARKER}/source.mkv".encode()

    async def _fake_subprocess(_cmd, _timeout):
        return 1, leaky_stderr

    monkeypatch.setattr(_remux, "_run_subprocess", _fake_subprocess)
    monkeypatch.setattr(_remux, "_check_remux_disk_space", lambda _src: None)

    error, rollback = await _remux._safe_remux(source, [0])

    assert error == "ffmpeg_failed"
    assert _LEAK_MARKER not in str(error)
    assert rollback is None


@pytest.mark.asyncio
async def test_safe_remux_returns_short_code_on_unexpected_exception(monkeypatch, tmp_path):
    """An unexpected exception inside the try block must surface as the
    short ``remux_error`` code with no embedded message."""
    from services.opensubtitles import _remux

    source = tmp_path / "movie.mkv"
    source.write_bytes(b"fake bytes")

    async def _raising_subprocess(_cmd, _timeout):
        raise RuntimeError(f"{_LEAK_MARKER} unexpected ffmpeg crash")

    monkeypatch.setattr(_remux, "_run_subprocess", _raising_subprocess)
    monkeypatch.setattr(_remux, "_check_remux_disk_space", lambda _src: None)

    error, rollback = await _remux._safe_remux(source, [0])

    assert error == "remux_error"
    assert _LEAK_MARKER not in str(error)
    assert rollback is None
