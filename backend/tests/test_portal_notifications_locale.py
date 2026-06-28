"""Bell notifications re-resolve media titles (request_*/ticket_*) to the
reader's locale at read time; non-media notifs (events) are left untouched (#288)."""
from __future__ import annotations

import pytest

from services.portal import media_title_localize as ml
from services.portal import notifications as notif_svc
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token


def _patch_localize(monkeypatch):
    """Force localize_titles to actually re-resolve via a stubbed TMDB."""
    ml._title_cache.clear()

    async def _key(db=None):
        return "test-key"

    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]"}

    monkeypatch.setattr("services.portal.media_title_localize._get_tmdb_key", _key)
    monkeypatch.setattr("services.portal.media_title_localize.get_media_detail", _detail)


@pytest.mark.asyncio
async def test_request_notification_title_localized_on_read(db_session, monkeypatch):
    user, _ = await make_portal_user(db_session, username="notif-a", display_name="V", role="viewer")
    await notif_svc.create(db_session, user.id, "request_approved", {
        "tmdb_id": 603, "media_type": "movie", "title": "Matrice", "request_id": 1,
    })
    _patch_localize(monkeypatch)

    result = await notif_svc.list_for_user(db_session, user.id, locale="en")
    assert result["items"][0]["payload"]["title"] == "T603 [en]"


@pytest.mark.asyncio
async def test_ticket_notification_title_localized_on_read(db_session, monkeypatch):
    user, _ = await make_portal_user(db_session, username="notif-b", display_name="V", role="viewer")
    await notif_svc.create(db_session, user.id, "ticket_replied", {
        "ticket_id": 7, "title": "Trône", "tmdb_id": 1399, "media_type": "series",
    })
    _patch_localize(monkeypatch)

    result = await notif_svc.list_for_user(db_session, user.id, locale="en")
    assert result["items"][0]["payload"]["title"] == "T1399 [en]"


@pytest.mark.asyncio
async def test_non_media_notification_untouched(db_session, monkeypatch):
    user, _ = await make_portal_user(db_session, username="notif-c", display_name="V", role="viewer")
    await notif_svc.create(db_session, user.id, "event_invitation", {
        "from": "alice", "title": "Movie Night",
    })
    _patch_localize(monkeypatch)

    result = await notif_svc.list_for_user(db_session, user.id, locale="en")
    # No tmdb_id -> title kept as-is even in a non-default locale.
    assert result["items"][0]["payload"]["title"] == "Movie Night"


@pytest.mark.asyncio
async def test_default_locale_is_noop(db_session, monkeypatch):
    user, _ = await make_portal_user(db_session, username="notif-d", display_name="V", role="viewer")
    await notif_svc.create(db_session, user.id, "request_approved", {
        "tmdb_id": 603, "media_type": "movie", "title": "Matrice", "request_id": 1,
    })
    _patch_localize(monkeypatch)

    result = await notif_svc.list_for_user(db_session, user.id, locale="fr")
    assert result["items"][0]["payload"]["title"] == "Matrice"


@pytest.mark.asyncio
async def test_notifications_endpoint_passes_request_locale(client, db_session, monkeypatch):
    user, _ = await make_portal_user(db_session, username="notif-e", display_name="V", role="viewer")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    captured = {}

    async def _fake(db, user_id, unread_only=False, limit=10, cursor=None, locale="fr"):
        captured["locale"] = locale
        return {"items": [], "total": 0, "next_cursor": None, "has_more": False}

    monkeypatch.setattr("services.portal.notifications.list_for_user", _fake)
    r = await client.get("/api/portal/notifications", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["locale"] == "en"
