"""Guard tests pinning the short error code contract on cycle 22 routes.

Cycle 22 replaced two sites in services/logs/_files.py:read_log_file
and services/emby/library.py:refresh_library that previously
embedded `str(exc)` in the response body. Without these tests a
future refactor could silently regress to leaking the exception
text between nightly CodeQL py/stack-trace-exposure scans.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


_LEAK_MARKER = "/secret/path"


# services/logs/_files.py — read_log_file


def test_read_log_file_returns_short_code_on_exception(monkeypatch, tmp_path):
    from services.logs import _files as logs_files_module

    log_file = tmp_path / "playback.txt"
    log_file.write_text("line1\nline2\n", encoding="utf-8")

    # Bypass the filename regex and root containment so the helper resolves
    # to our tmp log file, then force the file-open path to raise with the
    # leak marker embedded in the exception message.
    monkeypatch.setattr(logs_files_module, "_safe_log_path", lambda _name: log_file)

    def _raise_on_open(*_args, **_kwargs):
        raise RuntimeError(f"{_LEAK_MARKER} read boom")

    monkeypatch.setattr("builtins.open", _raise_on_open)

    result = logs_files_module.read_log_file("playback.txt", lines=10)

    assert result == {"error": "log_read_failed", "lines": [], "total_lines": 0}
    assert _LEAK_MARKER not in str(result)


# services/emby/library.py — refresh_library


@pytest.mark.asyncio
async def test_refresh_library_returns_short_code_on_exception(monkeypatch):
    from services.emby import library as emby_library_module

    fake_client = AsyncMock()
    fake_client.post = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} boom"))

    with patch(
        "services.emby.library._get_emby_config",
        new=AsyncMock(return_value=("http://emby.example", "k")),
    ), patch.object(emby_library_module, "get_internal_client", lambda: fake_client):
        result = await emby_library_module.refresh_library(db=AsyncMock())

    assert result == {"error": "refresh_library_failed"}
    assert _LEAK_MARKER not in str(result)
