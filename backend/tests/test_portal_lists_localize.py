"""Per-viewer localization of user-list titles (rows, history, CSV export).

``UserListItem.title`` / ``UserListHistory.title`` are frozen in the adder's
language; a viewer on a non-default locale (X-MK-Locale) gets them re-resolved
via TMDB (stubbed here), cached per (tmdb_id, media_type, lang). The default
locale is served as-is and the input dicts are never mutated.
"""
from __future__ import annotations

import pytest

from core.security import hash_password
from models.portal.social import UserList, UserListItem
from models.user import User
from services.portal import media_title_localize as ll
from services.portal import lists_query as svc_query


def _items() -> list[dict]:
    return [
        {"tmdb_id": 603, "media_type": "movie", "title": "Matrice", "year": 1999},
        {"tmdb_id": 1399, "media_type": "tv", "title": "Trone", "year": 2011},
        {"tmdb_id": None, "media_type": "movie", "title": "No TMDB"},
    ]


async def _fake_key(db=None):
    return "test-key"


def _patch(monkeypatch, detail):
    ll._title_cache.clear()
    monkeypatch.setattr("services.portal.media_title_localize._get_tmdb_key", _fake_key)
    monkeypatch.setattr("services.portal.media_title_localize.get_media_detail", detail)


@pytest.mark.asyncio
async def test_default_locale_served_as_is(monkeypatch):
    called = []

    async def _detail(mt, tid, db=None, locale=None):
        called.append(tid)
        return {}

    _patch(monkeypatch, _detail)
    items = _items()
    out = await ll.localize_titles(None, items, "fr")
    assert out is items
    assert called == []


@pytest.mark.asyncio
async def test_localizes_title_only(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]", "overview": "ignored"}

    _patch(monkeypatch, _detail)
    out = await ll.localize_titles(None, _items(), "en")
    assert out[0]["title"] == "T603 [en]"
    assert out[0]["year"] == 1999  # other fields preserved
    assert "overview" not in out[0]  # title-only: no overview leaked in
    assert out[1]["title"] == "T1399 [en]"
    assert out[2]["title"] == "No TMDB"  # no tmdb_id -> untouched


@pytest.mark.asyncio
async def test_does_not_mutate_input(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": "X"}

    _patch(monkeypatch, _detail)
    items = _items()
    await ll.localize_titles(None, items, "en")
    assert items[0]["title"] == "Matrice"


@pytest.mark.asyncio
async def test_blank_or_error_keeps_stored_title(monkeypatch):
    async def _blank(mt, tid, db=None, locale=None):
        return {"title": ""}

    _patch(monkeypatch, _blank)
    out = await ll.localize_titles(None, _items(), "en")
    assert out[0]["title"] == "Matrice"

    async def _err(mt, tid, db=None, locale=None):
        return {"error": "tmdb_detail_failed"}

    _patch(monkeypatch, _err)
    out = await ll.localize_titles(None, _items(), "en")
    assert out[0]["title"] == "Matrice"


@pytest.mark.asyncio
async def test_no_tmdb_key_serves_as_is(monkeypatch):
    ll._title_cache.clear()
    called = []

    async def _no_key(db=None):
        return ""

    async def _detail(mt, tid, db=None, locale=None):
        called.append(tid)
        return {}

    monkeypatch.setattr("services.portal.media_title_localize._get_tmdb_key", _no_key)
    monkeypatch.setattr("services.portal.media_title_localize.get_media_detail", _detail)
    items = _items()
    out = await ll.localize_titles(None, items, "en")
    assert out is items
    assert called == []


@pytest.mark.asyncio
async def test_cache_avoids_second_tmdb_call(monkeypatch):
    calls = []

    async def _detail(mt, tid, db=None, locale=None):
        calls.append(tid)
        return {"title": f"T{tid}"}

    _patch(monkeypatch, _detail)
    await ll.localize_titles(None, _items(), "en")
    await ll.localize_titles(None, _items(), "en")
    assert sorted(calls) == [603, 1399]


@pytest.mark.asyncio
async def test_get_list_localizes_item_titles(db_session, monkeypatch):
    user = User(
        username="list-i18n",
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    lst = UserList(user_id=user.id, name="My films")
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)
    db_session.add(UserListItem(
        list_id=lst.id, tmdb_id=603, media_type="movie", title="Matrice",
    ))
    await db_session.commit()

    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]"}

    _patch(monkeypatch, _detail)
    res = await svc_query.get_list(db_session, lst.id, user.id, locale="en")
    assert any(it["title"] == "T603 [en]" for it in res["items"])

    ll._title_cache.clear()
    res_fr = await svc_query.get_list(db_session, lst.id, user.id, locale="fr")  # default -> as-is
    assert any(it["title"] == "Matrice" for it in res_fr["items"])


@pytest.mark.asyncio
async def test_get_history_localizes_titles(db_session, monkeypatch):
    """The list audit log (owner/contributor only) re-resolves item titles."""
    from models.portal.social import UserListHistory
    from services.portal import lists_admin

    user = User(
        username="list-hist-i18n",
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    lst = UserList(user_id=user.id, name="My films")
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)
    db_session.add(UserListHistory(
        list_id=lst.id, user_id=user.id, action="add",
        tmdb_id=603, media_type="movie", title="Matrice",
    ))
    await db_session.commit()

    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]"}

    _patch(monkeypatch, _detail)
    hist = await lists_admin.get_history(db_session, lst.id, user.id, locale="en")
    assert any(h["title"] == "T603 [en]" for h in hist)


@pytest.mark.asyncio
async def test_export_csv_localizes_titles(db_session, monkeypatch):
    """The CSV export's title column is localized before serialization."""
    from services.portal import lists_admin

    user = User(
        username="list-export-i18n",
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    lst = UserList(user_id=user.id, name="My films")
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)
    db_session.add(UserListItem(
        list_id=lst.id, tmdb_id=603, media_type="movie", title="Matrice", year=1999,
    ))
    await db_session.commit()

    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]"}

    _patch(monkeypatch, _detail)
    out = await lists_admin.export_list(db_session, lst.id, user.id, fmt="csv", locale="en")
    assert "T603 [en]" in out["content"]
