"""Admin news edit/delete via the ``/api/portal/news`` surface.

The PUT/DELETE routes are gated by ``require_admin`` (portal scope) and
power the AdminNews edit/delete buttons. These tests exercise the full
HTTP path so a future refactor of the schema or the dependency wiring
trips the suite before it ships.
"""
from __future__ import annotations

import pytest

from tests._portal_profile_helpers import PORTAL_COOKIE, portal_token, make_portal_user


async def _seed_admin(db_session) -> str:
    """Create a portal-scope admin user and return their username."""
    user, _profile = await make_portal_user(
        db_session,
        username="news-admin",
        display_name="News Admin",
        role="admin",
    )
    return user.username


def _auth(client, username: str) -> None:
    client.cookies.set(PORTAL_COOKIE, portal_token(username))


@pytest.mark.asyncio
async def test_update_news_returns_success(client, db_session):
    username = await _seed_admin(db_session)
    _auth(client, username)

    resp = await client.post("/api/portal/news", json={
        "title": "Original",
        "content": "Old body",
        "type": "announcement",
    })
    assert resp.status_code == 200, resp.text
    news_id = resp.json()["id"]

    resp = await client.put(
        f"/api/portal/news/{news_id}",
        json={"title": "Updated", "content": "New body"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True

    resp = await client.get("/api/portal/news/admin")
    items = resp.json()["items"]
    match = next((it for it in items if it["id"] == news_id), None)
    assert match is not None
    assert match["title"] == "Updated"
    assert match["content"] == "New body"


@pytest.mark.asyncio
async def test_update_news_rejects_unknown_field(client, db_session):
    """Pydantic ``extra='forbid'`` keeps the admin update surface tight."""
    username = await _seed_admin(db_session)
    _auth(client, username)

    resp = await client.post("/api/portal/news", json={
        "title": "Original",
        "content": "Body",
    })
    news_id = resp.json()["id"]

    resp = await client.put(
        f"/api/portal/news/{news_id}",
        json={"title": "ok", "bogus_field": "nope"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_news_then_404(client, db_session):
    username = await _seed_admin(db_session)
    _auth(client, username)

    resp = await client.post("/api/portal/news", json={
        "title": "To delete",
        "content": "Body",
    })
    news_id = resp.json()["id"]

    resp = await client.delete(f"/api/portal/news/{news_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True

    resp = await client.delete(f"/api/portal/news/{news_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_missing_news_returns_404(client, db_session):
    username = await _seed_admin(db_session)
    _auth(client, username)

    resp = await client.put(
        "/api/portal/news/999999",
        json={"title": "Whatever"},
    )
    assert resp.status_code == 404
