"""/library/continue must scope to the viewer's Emby user, never server-wide.

The carousel previously queried Emby's server-wide ``/Items`` with the admin
API key, leaking every user's in-progress titles. It must pass the viewer's
emby_user_id and fail closed (empty list) when that id is unknown rather than
fall back to the server-wide query.
"""
from __future__ import annotations

import pytest

from services.portal.available_continue import get_continue_watching
from tests._portal_profile_helpers import PORTAL_COOKIE, portal_token, make_portal_user


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", [None, ""])
async def test_continue_returns_empty_without_emby_user_id(missing):
    # Fail closed: no Emby user id → no server-wide query, just an empty list.
    assert await get_continue_watching(None, emby_user_id=missing) == []


@pytest.mark.asyncio
async def test_continue_endpoint_passes_viewer_emby_id(client, db_session, monkeypatch):
    user, _profile = await make_portal_user(
        db_session,
        username="cont-viewer",
        display_name="V",
        role="viewer",
        emby_user_id="EMBY_USER_B",
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    captured = {}

    async def _fake_continue(db, emby_user_id=None, limit=10):
        captured["emby_user_id"] = emby_user_id
        return []

    monkeypatch.setattr("services.portal.available.get_continue_watching", _fake_continue)

    r = await client.get("/api/portal/library/continue")
    assert r.status_code == 200, r.text
    assert captured["emby_user_id"] == "EMBY_USER_B"
