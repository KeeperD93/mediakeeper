"""Per-viewer localization of ticket media titles (list / detail / drawer).

``Ticket.media_title`` is frozen in the reporter's language. A viewer on a
non-default locale gets it re-resolved via TMDB (stubbed), reusing the shared
``media_title_localize`` helper with ``title_key="media_title"`` and the
``series`` -> ``tv`` alias (tickets use "series", TMDB uses "tv").
"""
from __future__ import annotations

import pytest

from core.security import hash_password
from models.portal.ticket import Ticket
from models.user import User
from services.portal import media_title_localize as ml
from services.portal import tickets as ticket_svc


async def _fake_key(db=None):
    return "test-key"


def _patch(monkeypatch, detail):
    ml._title_cache.clear()
    monkeypatch.setattr("services.portal.media_title_localize._get_tmdb_key", _fake_key)
    monkeypatch.setattr("services.portal.media_title_localize.get_media_detail", detail)


@pytest.mark.asyncio
async def test_title_key_and_series_alias(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{mt}]"}

    _patch(monkeypatch, _detail)
    items = [
        {"tmdb_id": 900002, "media_type": "series", "media_title": "Série Exemple"},  # series -> tv
        {"tmdb_id": 900001, "media_type": "movie", "media_title": "Film Exemple"},
        {"tmdb_id": None, "media_type": "season", "media_title": "S1"},  # no tmdb_id -> skip
        {"tmdb_id": 5, "media_type": "other", "media_title": "Off-library"},  # unmapped -> skip
    ]
    out = await ml.localize_titles(None, items, "en", title_key="media_title")
    assert out[0]["media_title"] == "T900002 [tv]"  # series mapped to the TMDB tv type
    assert out[1]["media_title"] == "T900001 [movie]"
    assert out[2]["media_title"] == "S1"  # no tmdb_id -> untouched
    assert out[3]["media_title"] == "Off-library"  # "other" not a TMDB type -> untouched


@pytest.mark.asyncio
async def test_list_tickets_localizes_media_title(db_session, monkeypatch):
    user = User(
        username="ticket-i18n",
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    db_session.add(Ticket(
        user_id=user.id, tmdb_id=900002, media_title="Série Exemple", media_type="series",
        issue_type="video", description="x",
    ))
    await db_session.commit()

    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]"}

    _patch(monkeypatch, _detail)
    res = await ticket_svc.list_tickets(db_session, user.id, page=1, locale="en")
    assert any(it["media_title"] == "T900002 [en]" for it in res["items"])

    ml._title_cache.clear()
    res_fr = await ticket_svc.list_tickets(db_session, user.id, page=1, locale="fr")  # default -> as-is
    assert any(it["media_title"] == "Série Exemple" for it in res_fr["items"])


@pytest.mark.asyncio
async def test_admin_drawer_tickets_localizes(db_session, monkeypatch):
    """The admin user-drawer Tickets tab re-resolves titles too.

    Unlike the ticket service (``title_key="media_title"``), the drawer
    aliases ``media_title`` onto the default ``title`` key and relies on the
    ``tmdb_id`` field, so this pins both the default-key path and the
    ``series`` -> ``tv`` alias on the admin feed.
    """
    from services.portal import admin_users_feed

    user = User(
        username="ticket-drawer-i18n",
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    db_session.add(Ticket(
        user_id=user.id, tmdb_id=900002, media_title="Série Exemple", media_type="series",
        issue_type="video", description="x",
    ))
    await db_session.commit()

    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{mt}/{locale}]"}

    _patch(monkeypatch, _detail)
    res = await admin_users_feed.list_user_tickets(db_session, user.id, locale="en")
    assert any(it["title"] == "T900002 [tv/en]" for it in res["items"])  # series -> tv
