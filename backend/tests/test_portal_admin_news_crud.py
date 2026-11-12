"""Admin news edit/delete via the ``/api/portal/news`` surface.

The PUT/DELETE routes are gated by ``require_admin`` (portal scope) and
power the AdminNews edit/delete buttons. These tests exercise the full
HTTP path so a future refactor of the schema or the dependency wiring
trips the suite before it ships.
"""
from __future__ import annotations

import logging

import pytest
from fastapi import HTTPException

from api.portal import news as news_routes
from services.portal import news as news_svc
from tests._portal_profile_helpers import PORTAL_COOKIE, portal_token, make_portal_user

# An inverted publication window: it ends before it starts.
INVERTED_WINDOW = {"start_at": "2030-01-02T00:00:00Z", "end_at": "2030-01-01T00:00:00Z"}


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


@pytest.mark.asyncio
async def test_inverted_window_answers_its_code_on_create_and_update(client, db_session, caplog):
    _auth(client, await _seed_admin(db_session))
    news_id = (await client.post("/api/portal/news", json={"title": "Test", "content": "Body"})).json()["id"]

    with caplog.at_level(logging.WARNING, logger="mediakeeper.portal.news"):
        created = await client.post("/api/portal/news", json={
            "title": "Test", "content": "Body", **INVERTED_WINDOW,
        })
        updated = await client.put(f"/api/portal/news/{news_id}", json=INVERTED_WINDOW)

    for resp in (created, updated):
        assert resp.status_code == 400
        assert resp.json() == {"detail": "start_at_must_precede_end_at"}
    assert caplog.text.count("start_at_must_precede_end_at") == 2  # both stay visible server-side


@pytest.mark.asyncio
@pytest.mark.parametrize("service_fn, method", [("create_news", "post"), ("update_news", "put")])
async def test_an_unexpected_error_text_never_reaches_the_client(
    client, db_session, monkeypatch, service_fn, method,
):
    """Only the known input code becomes a 400: any other error reaches the
    global handler (generic 500) instead of echoing its message."""
    _auth(client, await _seed_admin(db_session))
    news_id = (await client.post("/api/portal/news", json={"title": "Test", "content": "Body"})).json()["id"]

    async def _boom(*_args, **_kwargs):
        raise ValueError("internal detail")

    monkeypatch.setattr(news_svc, service_fn, _boom)
    url = "/api/portal/news" if method == "post" else f"/api/portal/news/{news_id}"
    with pytest.raises(ValueError, match="internal detail"):
        await getattr(client, method)(url, json={"title": "Test", "content": "Body"})


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["create", "update"])
async def test_rejection_keeps_the_service_error_as_cause(db_session, route):
    user, profile = await make_portal_user(db_session, username="news-admin", role="admin")
    admin = (user, profile)
    if route == "create":
        call = news_routes.create_news(
            news_routes.CreateNews(title="Test", content="Body", **INVERTED_WINDOW),
            admin=admin, db=db_session,
        )
    else:
        created = await news_svc.create_news(
            db_session, user.id, news_routes.CreateNews(title="Test", content="Body").model_dump(),
        )
        call = news_routes.update_news(
            created["id"], news_routes.UpdateNews(**INVERTED_WINDOW), admin=admin, db=db_session,
        )

    with pytest.raises(HTTPException) as caught:
        await call

    assert caught.value.status_code == 400
    assert isinstance(caught.value.__cause__, news_svc.NewsInputError)
