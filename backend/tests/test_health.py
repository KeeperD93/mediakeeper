"""Tests for /api/health."""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from api.changelog import APP_VERSION
from core.security import create_access_token

# Default backoffice allowlist is {"admin"}, so this username passes
# is_backoffice_admin without touching MK_ADMIN_USERS.
_FAKE_ADMIN = SimpleNamespace(username="admin", is_active=True, tokens_invalidated_at=None)


class _FakeAsyncSessionContext:
    def __init__(self, admin_user=None):
        # Same mock backs the Setting probe (result ignored) and the admin
        # lookup of the full-health auth gate.
        result = SimpleNamespace(scalar_one_or_none=lambda: admin_user)
        self._session = SimpleNamespace(execute=AsyncMock(return_value=result))

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    """GET /api/health doit returnr status ok et la version."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "version" in data
    assert "database" in data


@pytest.mark.asyncio
async def test_health_contains_version(client):
    """The health response must contain the version number."""
    resp = await client.get("/api/health")
    data = resp.json()
    assert data["version"] == APP_VERSION


@pytest.mark.asyncio
async def test_health_full_checks_configured_media_source(client):
    """GET /api/health?full=1 should probe the configured media source
    when called by an authenticated admin (#388)."""
    client.cookies.set("mk_token", create_access_token({"sub": "admin", "scope": "admin"}))
    fake_client = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(is_success=True, status_code=200)),
    )

    with (
        patch("api.core_routes.AsyncSession", side_effect=lambda *_args, **_kwargs: _FakeAsyncSessionContext(_FAKE_ADMIN)),
        patch(
            "api.core_routes.get_active_media_source",
            AsyncMock(return_value={"source": "emby", "url": "http://emby.local", "api_key": "abc"}),
        ),
        patch("api.core_routes.get_internal_client", return_value=fake_client),
    ):
        resp = await client.get("/api/health?full=1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["media_source"] == "emby"
    assert data["media_source_status"] == "ok"
    fake_client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_full_returns_503_when_configured_media_source_is_down(client):
    """GET /api/health?full=1 should surface media source outages."""
    client.cookies.set("mk_token", create_access_token({"sub": "admin", "scope": "admin"}))
    fake_client = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(is_success=False, status_code=503)),
    )

    with (
        patch("api.core_routes.AsyncSession", side_effect=lambda *_args, **_kwargs: _FakeAsyncSessionContext(_FAKE_ADMIN)),
        patch(
            "api.core_routes.get_active_media_source",
            AsyncMock(return_value={"source": "emby", "url": "http://emby.local", "api_key": "abc"}),
        ),
        patch("api.core_routes.get_internal_client", return_value=fake_client),
    ):
        resp = await client.get("/api/health?full=1")

    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["media_source"] == "emby"
    assert data["media_source_status"] == "http_503"


@pytest.mark.asyncio
async def test_health_full_without_admin_falls_back_to_basic(client):
    """An unauthenticated ?full=1 must not expose media_source nor probe the
    upstream — it degrades to the public basic payload (#388)."""
    fake_client = SimpleNamespace(get=AsyncMock())

    with (
        patch("api.core_routes.AsyncSession", side_effect=lambda *_args, **_kwargs: _FakeAsyncSessionContext()),
        patch(
            "api.core_routes.get_active_media_source",
            AsyncMock(return_value={"source": "emby", "url": "http://emby.local", "api_key": "abc"}),
        ),
        patch("api.core_routes.get_internal_client", return_value=fake_client),
    ):
        resp = await client.get("/api/health?full=1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "media_source" not in data
    fake_client.get.assert_not_awaited()
