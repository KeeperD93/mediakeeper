"""Per-viewer localization of request titles (moderation + user lists).

``MediaRequest.title`` is frozen in the requester's language at creation. A
viewer on a non-default locale (X-MK-Locale) gets it re-resolved via TMDB
(stubbed here), cached per (id, media_type, lang); the default locale is served
as-is and the input dicts are never mutated.
"""
from __future__ import annotations

import pytest

from core.security import hash_password
from models.portal.request import MediaRequest
from models.user import User
from services.portal import requests as req_svc
from services.portal import requests_localize as rl


def _items() -> list[dict]:
    return [
        {"tmdb_id": 603, "media_type": "movie", "title": "Matrice", "status": "pending"},
        {"tmdb_id": 1399, "media_type": "tv", "title": "Trone", "status": "approved"},
        {"tmdb_id": None, "media_type": "movie", "title": "No TMDB", "status": "pending"},
    ]


async def _fake_key(db=None):
    return "test-key"


def _patch(monkeypatch, detail):
    rl._title_cache.clear()
    monkeypatch.setattr("services.portal.requests_localize._get_tmdb_key", _fake_key)
    monkeypatch.setattr("services.portal.requests_localize.get_media_detail", detail)


@pytest.mark.asyncio
async def test_default_locale_served_as_is(monkeypatch):
    called = []

    async def _detail(mt, tid, db=None, locale=None):
        called.append(tid)
        return {}

    _patch(monkeypatch, _detail)
    items = _items()
    out = await rl.localize_request_titles(None, items, "fr")
    assert out is items
    assert called == []


@pytest.mark.asyncio
async def test_localizes_title_only(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]", "overview": "ignored"}

    _patch(monkeypatch, _detail)
    out = await rl.localize_request_titles(None, _items(), "en")
    assert out[0]["title"] == "T603 [en]"
    assert out[0]["status"] == "pending"  # other fields preserved
    assert "overview" not in out[0]  # title-only: no overview leaked in
    assert out[1]["title"] == "T1399 [en]"
    assert out[2]["title"] == "No TMDB"  # no tmdb_id -> untouched


@pytest.mark.asyncio
async def test_does_not_mutate_input(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": "X"}

    _patch(monkeypatch, _detail)
    items = _items()
    await rl.localize_request_titles(None, items, "en")
    assert items[0]["title"] == "Matrice"


@pytest.mark.asyncio
async def test_blank_or_error_keeps_stored_title(monkeypatch):
    async def _blank(mt, tid, db=None, locale=None):
        return {"title": ""}

    _patch(monkeypatch, _blank)
    out = await rl.localize_request_titles(None, _items(), "en")
    assert out[0]["title"] == "Matrice"

    async def _err(mt, tid, db=None, locale=None):
        return {"error": "tmdb_detail_failed"}

    _patch(monkeypatch, _err)
    out = await rl.localize_request_titles(None, _items(), "en")
    assert out[0]["title"] == "Matrice"


@pytest.mark.asyncio
async def test_no_tmdb_key_serves_as_is(monkeypatch):
    rl._title_cache.clear()
    called = []

    async def _no_key(db=None):
        return ""

    async def _detail(mt, tid, db=None, locale=None):
        called.append(tid)
        return {}

    monkeypatch.setattr("services.portal.requests_localize._get_tmdb_key", _no_key)
    monkeypatch.setattr("services.portal.requests_localize.get_media_detail", _detail)
    items = _items()
    out = await rl.localize_request_titles(None, items, "en")
    assert out is items
    assert called == []


@pytest.mark.asyncio
async def test_cache_avoids_second_tmdb_call(monkeypatch):
    calls = []

    async def _detail(mt, tid, db=None, locale=None):
        calls.append(tid)
        return {"title": f"T{tid}"}

    _patch(monkeypatch, _detail)
    await rl.localize_request_titles(None, _items(), "en")
    await rl.localize_request_titles(None, _items(), "en")
    assert sorted(calls) == [603, 1399]


@pytest.mark.asyncio
async def test_list_requests_service_localizes(db_session, monkeypatch):
    user = User(
        username="req-i18n",
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    db_session.add(MediaRequest(
        user_id=user.id, tmdb_id=603, media_type="movie", title="Matrice", status="pending",
    ))
    await db_session.commit()

    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]"}

    _patch(monkeypatch, _detail)
    resp = await req_svc.list_requests(db_session, locale="en")
    assert any(it["title"] == "T603 [en]" for it in resp["items"])

    rl._title_cache.clear()
    resp_fr = await req_svc.list_requests(db_session, locale="fr")  # default -> as-is
    assert any(it["title"] == "Matrice" for it in resp_fr["items"])
