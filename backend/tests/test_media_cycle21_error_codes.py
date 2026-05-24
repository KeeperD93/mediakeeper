"""Guard tests pinning the short error code contract on cycle 21 routes.

Cycle 21 replaced six sites in api/settings.py:ping_tool,
api/stats/_import.py:import_jellystats and
api/portal/catalog/_browse.py:watch_providers that previously embedded
`str(exc)` (or path fragments) in the response body. Without these tests
a future refactor could silently regress to leaking the exception text
between nightly CodeQL py/stack-trace-exposure scans.

The two stats import guards live in backend/tests/test_stats_import.py
with the existing jellystats coverage (module locality); this file covers
the four remaining routes — three settings ping_tool variants
(opensubtitles, tmdb, generic URL) and the portal watch_providers debug
helper.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


_LEAK_MARKER = "/secret/path"


# api/settings.py — ping_tool branches


@pytest.mark.asyncio
async def test_ping_tool_opensubtitles_returns_short_code_on_exception(monkeypatch):
    from api import settings as settings_module

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} boom"))
    monkeypatch.setattr(
        settings_module, "get_tools_config",
        AsyncMock(return_value={"opensubtitles": {"enabled": True, "api_key": "k"}}),
    )
    monkeypatch.setattr(settings_module, "get_external_client", lambda: fake_client)

    result = await settings_module.ping_tool("opensubtitles", db=AsyncMock(), _=MagicMock())

    assert result == {"online": False, "reason": "tool_ping_failed"}
    assert _LEAK_MARKER not in str(result)


@pytest.mark.asyncio
async def test_ping_tool_tmdb_returns_short_code_on_exception(monkeypatch):
    from api import settings as settings_module

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} boom"))
    monkeypatch.setattr(
        settings_module, "get_tools_config",
        AsyncMock(return_value={"tmdb": {"enabled": True, "api_key": "k"}}),
    )
    monkeypatch.setattr(settings_module, "get_external_client", lambda: fake_client)

    result = await settings_module.ping_tool("tmdb", db=AsyncMock(), _=MagicMock())

    assert result == {"online": False, "reason": "tool_ping_failed"}
    assert _LEAK_MARKER not in str(result)


@pytest.mark.asyncio
async def test_ping_tool_generic_url_returns_short_code_on_exception(monkeypatch):
    from api import settings as settings_module

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} boom"))
    monkeypatch.setattr(
        settings_module, "get_tools_config",
        AsyncMock(return_value={"emby": {"enabled": True, "url": "https://emby.example/"}}),
    )
    monkeypatch.setattr(settings_module, "get_internal_client", lambda: fake_client)

    result = await settings_module.ping_tool("emby", db=AsyncMock(), _=MagicMock())

    assert result == {"online": False, "reason": "tool_ping_failed"}
    assert _LEAK_MARKER not in str(result)


# api/portal/catalog/_browse.py — watch_providers debug helper


@pytest.mark.asyncio
async def test_watch_providers_returns_short_code_on_exception(monkeypatch):
    from api.portal.catalog import _browse as catalog_browse

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError(f"{_LEAK_MARKER} boom"))

    with patch("core.http_client.get_external_client", return_value=fake_client), \
         patch("services.tmdb._get_tmdb_key", new=AsyncMock(return_value="k")):
        result = await catalog_browse.watch_providers(
            region="FR",
            media_type="movie",
            up=(MagicMock(), MagicMock()),
            db=AsyncMock(),
        )

    assert result == {"error": "watch_providers_failed", "items": []}
    assert _LEAK_MARKER not in str(result)
