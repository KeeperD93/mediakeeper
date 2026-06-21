"""Authorization contract for the watch-providers debug helper.

``GET /api/portal/catalog/watch-providers`` is an admin-only maintainer
lookup (no live UI consumer): it must reject non-admin portal users with
403 ``admin_required`` and let admins through.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)

_URL = "/api/portal/catalog/watch-providers?region=FR&media_type=movie"


@pytest.mark.asyncio
async def test_watch_providers_rejects_non_admin(client, db_session):
    viewer, _ = await make_portal_user(db_session, username="viewer", role="viewer")
    client.cookies.set(PORTAL_COOKIE, portal_token(viewer.username))

    resp = await client.get(_URL)

    assert resp.status_code == 403
    assert resp.json()["detail"] == "admin_required"


@pytest.mark.asyncio
async def test_watch_providers_allows_admin(client, db_session):
    admin, _ = await make_portal_user(db_session, username="admin", role="admin")
    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json = MagicMock(return_value={
        "results": [
            {"provider_id": 1, "provider_name": "Test Provider",
             "display_priorities": {"FR": 1}},
        ],
    })
    fake_client = AsyncMock()
    fake_client.get = AsyncMock(return_value=fake_resp)

    with patch("core.http_client.get_external_client", return_value=fake_client), \
         patch("services.tmdb._get_tmdb_key", new=AsyncMock(return_value="k")):
        resp = await client.get(_URL)

    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["items"][0]["provider_name"] == "Test Provider"


@pytest.mark.asyncio
async def test_catalog_videos_rejects_invalid_media_type(client, db_session):
    """media_type is pinned to movie|tv so it can't inject a query string
    into the upstream TMDB URL (#420)."""
    viewer, _ = await make_portal_user(db_session, username="viewer_vids", role="viewer")
    client.cookies.set(PORTAL_COOKIE, portal_token(viewer.username))

    resp = await client.get("/api/portal/catalog/videos/notatype/550")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_catalog_detail_rejects_invalid_media_type(client, db_session):
    viewer, _ = await make_portal_user(db_session, username="viewer_det", role="viewer")
    client.cookies.set(PORTAL_COOKIE, portal_token(viewer.username))

    resp = await client.get("/api/portal/catalog/detail/notatype/550")
    assert resp.status_code == 422
