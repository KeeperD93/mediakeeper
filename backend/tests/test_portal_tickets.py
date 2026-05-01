"""Tests for the portal ticket creation flow + Emby autocomplete endpoints."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, update

from models.portal.event import MKNotification
from models.portal.ticket import Ticket
from services.portal.tickets import auto_close_resolved_tickets
from tests._portal_profile_helpers import (
    PORTAL_COOKIE,
    make_portal_user,
    portal_token,
)


def _fake_response(*, status_code=200, payload=None):
    return SimpleNamespace(
        status_code=status_code,
        json=lambda: payload,
    )


async def _seed(client, db_session, *, username="ticketer", role="viewer"):
    user, profile = await make_portal_user(
        db_session, username=username, role=role
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(username))
    return user, profile


# ---------------------------------------------------------------------------
# Ticket creation — schema validation + persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_movie_ticket_persists_emby_anchor(client, db_session):
    await _seed(client, db_session)

    resp = await client.post("/api/portal/tickets", json={
        "emby_item_id": "emby-mov-1",
        "media_title": "Interstellar",
        "media_type": "movie",
        "issue_type": "audio",
        "description": "Audio désynchronisé après 30min",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["id"], int)


@pytest.mark.asyncio
async def test_creating_a_ticket_notifies_active_admins(client, db_session):
    """Each active admin (other than the author) must receive a
    ticket_created bell when a viewer files a ticket."""
    # Two admins + the author (viewer). Author + admin1 are active,
    # admin2 is inactive (must be skipped).
    await make_portal_user(db_session, username="admin-active", role="admin")
    inactive = await make_portal_user(db_session, username="admin-inactive", role="admin")
    inactive[1].account_active = False
    db_session.add(inactive[1])
    await db_session.commit()

    user, _ = await _seed(client, db_session, username="viewer-author")

    resp = await client.post("/api/portal/tickets", json={
        "media_title": "Bug",
        "media_type": "other",
        "issue_type": "other",
        "description": "Quelque chose cloche",
    })
    assert resp.status_code == 200, resp.text

    # Active admin got pinged, inactive admin didn't.
    rows = (await db_session.execute(
        select(MKNotification).where(MKNotification.type == "ticket_created")
    )).scalars().all()
    notified_user_ids = {n.user_id for n in rows}
    admin_active = (await db_session.execute(
        select(MKNotification).where(MKNotification.type == "ticket_created")
    )).scalars().first()
    assert admin_active is not None
    assert admin_active.payload.get("title") == "Bug"
    assert admin_active.payload.get("requester_id") == user.id
    # The author + the inactive admin must be excluded.
    assert user.id not in notified_user_ids
    assert inactive[0].id not in notified_user_ids


@pytest.mark.asyncio
async def test_auto_close_promotes_resolved_tickets_after_seven_days(client, db_session):
    """Resolved tickets older than 7 days flip to closed; fresher ones stay."""
    await _seed(client, db_session, username="ticketer-aged")

    # Two resolved tickets — we'll manually back-date one to 8 days ago.
    for desc in ("old one", "fresh one"):
        await client.post("/api/portal/tickets", json={
            "media_title": desc,
            "media_type": "other",
            "issue_type": "other",
            "description": desc,
        })
    rows = (await db_session.execute(select(Ticket))).scalars().all()
    rows.sort(key=lambda t: t.id)
    old, fresh = rows[0], rows[1]

    # Mark both resolved, then back-date `old.updated_at` past the cutoff.
    long_ago = datetime.now(timezone.utc) - timedelta(days=8)
    await db_session.execute(update(Ticket).where(Ticket.id == old.id).values(
        status="resolved", updated_at=long_ago,
    ))
    await db_session.execute(update(Ticket).where(Ticket.id == fresh.id).values(
        status="resolved",
    ))
    await db_session.commit()

    closed = await auto_close_resolved_tickets(db_session)
    assert closed == 1

    refreshed_old = await db_session.get(Ticket, old.id)
    refreshed_fresh = await db_session.get(Ticket, fresh.id)
    assert refreshed_old.status == "closed"
    assert refreshed_fresh.status == "resolved"


@pytest.mark.asyncio
async def test_list_tickets_filters_by_media_and_issue_type(client, db_session):
    """media_type + issue_type query params narrow the list (CSV multi-values)."""
    await _seed(client, db_session, username="ticketer-filters")

    payloads = [
        {"media_type": "other", "issue_type": "other", "media_title": "App bug"},
        {"media_type": "movie", "issue_type": "audio",
         "emby_item_id": "emby-mov-1", "media_title": "Mov audio"},
        {"media_type": "movie", "issue_type": "subtitles",
         "emby_item_id": "emby-mov-2", "media_title": "Mov subs"},
        {"media_type": "series", "issue_type": "subtitles",
         "series_emby_id": "emby-ser-1", "media_title": "Ser subs"},
    ]
    for p in payloads:
        resp = await client.post("/api/portal/tickets", json={**p, "description": "t"})
        assert resp.status_code == 200, resp.text

    # Movies + series only (no "other")
    resp = await client.get("/api/portal/tickets?media_type=movie,series")
    titles = {t["media_title"] for t in resp.json()["items"]}
    assert titles == {"Mov audio", "Mov subs", "Ser subs"}

    # Subtitle issues only — across any media type
    resp = await client.get("/api/portal/tickets?issue_type=subtitles")
    titles = {t["media_title"] for t in resp.json()["items"]}
    assert titles == {"Mov subs", "Ser subs"}

    # Combined: only movies with subtitle issue
    resp = await client.get("/api/portal/tickets?media_type=movie&issue_type=subtitles")
    titles = {t["media_title"] for t in resp.json()["items"]}
    assert titles == {"Mov subs"}

    # Invalid value falls back to "no filter" (silent drop)
    resp = await client.get("/api/portal/tickets?media_type=bogus")
    assert len(resp.json()["items"]) == 4


@pytest.mark.asyncio
async def test_admin_filing_their_own_ticket_does_not_self_notify(client, db_session):
    """Admins can file tickets too — they must not self-ping."""
    await make_portal_user(db_session, username="admin-other", role="admin")
    admin_user, _ = await _seed(client, db_session, username="admin-self", role="admin")

    resp = await client.post("/api/portal/tickets", json={
        "media_title": "Self ticket",
        "media_type": "other",
        "issue_type": "other",
        "description": "Bug repéré par un admin",
    })
    assert resp.status_code == 200, resp.text

    rows = (await db_session.execute(
        select(MKNotification).where(MKNotification.type == "ticket_created")
    )).scalars().all()
    assert all(n.user_id != admin_user.id for n in rows)
    # The other admin should still get the bell.
    assert any(n.user_id != admin_user.id for n in rows)


@pytest.mark.asyncio
async def test_get_ticket_returns_requester_and_reply_authors(client, db_session):
    """Detail payload must include requester + each reply's author block —
    the premium thread relies on display_name/avatar_url/role being present."""
    user, _ = await _seed(client, db_session, username="ticketer-requester")

    create = await client.post("/api/portal/tickets", json={
        "media_title": "Bug app",
        "media_type": "other",
        "issue_type": "other",
        "description": "Quelque chose cloche",
    })
    ticket_id = create.json()["id"]

    await client.post(f"/api/portal/tickets/{ticket_id}/reply", json={
        "content": "Précision de l'auteur",
    })

    resp = await client.get(f"/api/portal/tickets/{ticket_id}")
    data = resp.json()

    assert data["requester"] is not None
    assert data["requester"]["display_name"] == "ticketer-requester"
    assert data["requester"]["role"] == "viewer"
    assert data["replies"][0]["author"]["display_name"] == "ticketer-requester"


@pytest.mark.asyncio
async def test_create_series_ticket_with_selected_seasons(client, db_session):
    await _seed(client, db_session)

    resp = await client.post("/api/portal/tickets", json={
        "series_emby_id": "emby-ser-42",
        "media_title": "Severance",
        "media_type": "series",
        "selected_seasons": [
            {"season_number": 1, "episodes": [1, 2]},
            {"season_number": 2},
        ],
        "issue_type": "subtitles",
        "description": "Sous-titres FR manquants saison 1 ép. 1-2 + saison 2 entière",
    })
    assert resp.status_code == 200, resp.text

    ticket_id = resp.json()["id"]
    detail = await client.get(f"/api/portal/tickets/{ticket_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["media_type"] == "series"
    assert data["series_emby_id"] == "emby-ser-42"
    assert data["selected_seasons"] == [
        {"season_number": 1, "episodes": [1, 2]},
        {"season_number": 2},
    ]


@pytest.mark.asyncio
async def test_create_other_ticket_no_emby_anchor(client, db_session):
    """`other` is the off-library escape hatch — must accept zero anchors."""
    await _seed(client, db_session)

    resp = await client.post("/api/portal/tickets", json={
        "media_title": "Bug application",
        "media_type": "other",
        "issue_type": "other",
        "description": "Le bouton de la page profil ne réagit plus",
    })
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_movie_ticket_without_emby_id_is_rejected(client, db_session):
    await _seed(client, db_session)

    resp = await client.post("/api/portal/tickets", json={
        "media_title": "Inconnu",
        "media_type": "movie",
        "issue_type": "video",
        "description": "Pas de média réel",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_series_ticket_without_series_id_is_rejected(client, db_session):
    await _seed(client, db_session)

    resp = await client.post("/api/portal/tickets", json={
        "media_title": "Random show",
        "media_type": "series",
        "issue_type": "subtitles",
        "description": "Pas d'ancre série",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_other_ticket_with_emby_anchor_is_rejected(client, db_session):
    """`other` tickets must not carry library anchors — keeps the
    on/off-library distinction explicit."""
    await _seed(client, db_session)

    resp = await client.post("/api/portal/tickets", json={
        "emby_item_id": "emby-mov-99",
        "media_title": "Bug app + film",
        "media_type": "other",
        "issue_type": "other",
        "description": "Anchor accidentel",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Emby autocomplete endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emby_search_returns_shaped_hits(client, db_session):
    await _seed(client, db_session)

    fake_client = SimpleNamespace(get=AsyncMock(return_value=_fake_response(
        payload={"Items": [
            {
                "Id": "emby-mov-1",
                "Type": "Movie",
                "Name": "Interstellar",
                "OriginalTitle": "Interstellar",
                "ProductionYear": 2014,
                "ProviderIds": {"Tmdb": "157336"},
            },
            {
                "Id": "emby-ser-42",
                "Type": "Series",
                "Name": "Severance",
                "PremiereDate": "2022-02-18T00:00:00Z",
                "ProviderIds": {"Tmdb": "95396"},
            },
        ]},
    )))

    with patch("services.emby.search._get_emby_config", new=AsyncMock(
        return_value=("http://emby.test", "secret"),
    )), patch("services.emby.search.get_internal_client", return_value=fake_client):
        resp = await client.get("/api/portal/tickets/emby/search?q=inter")

    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 2

    movie = items[0]
    assert movie["type"] == "movie"
    assert movie["title"] == "Interstellar"
    assert movie["year"] == "2014"
    assert movie["tmdb_id"] == "157336"
    assert movie["poster_id"] == "emby-mov-1"

    series = items[1]
    assert series["type"] == "series"
    assert series["year"] == "2022"


@pytest.mark.asyncio
async def test_emby_search_empty_query_returns_empty(client, db_session):
    await _seed(client, db_session)

    resp = await client.get("/api/portal/tickets/emby/search?q=%20")
    # ``q`` is rejected by Field(min_length=1) when fully empty; whitespace-
    # only is accepted by FastAPI but trimmed to empty in the service layer.
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_emby_search_requires_auth(client):
    resp = await client.get("/api/portal/tickets/emby/search?q=test")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Series seasons endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_series_seasons_returns_episode_tree(client, db_session):
    await _seed(client, db_session)

    fake_client = SimpleNamespace(get=AsyncMock(side_effect=[
        # /Shows/{series_id}/Seasons
        _fake_response(payload={"Items": [
            {"Id": "season-1", "IndexNumber": 1, "Name": "Saison 1"},
            {"Id": "season-2", "IndexNumber": 2, "Name": "Saison 2"},
        ]}),
        # /Shows/{series_id}/Episodes for season 1
        _fake_response(payload={"Items": [
            {"Id": "ep-101", "IndexNumber": 1, "Name": "Pilot"},
            {"Id": "ep-102", "IndexNumber": 2, "Name": "Half Loop"},
        ]}),
        # /Shows/{series_id}/Episodes for season 2
        _fake_response(payload={"Items": [
            {"Id": "ep-201", "IndexNumber": 1, "Name": "Hello, Ms. Cobel"},
        ]}),
    ]))

    with patch("services.emby.search._get_emby_config", new=AsyncMock(
        return_value=("http://emby.test", "secret"),
    )), patch("services.emby.search.get_internal_client", return_value=fake_client):
        resp = await client.get("/api/portal/tickets/emby/series/emby-ser-42/seasons")

    assert resp.status_code == 200, resp.text
    seasons = resp.json()["seasons"]
    assert [s["season_number"] for s in seasons] == [1, 2]
    assert seasons[0]["episodes"][0]["episode_number"] == 1
    assert seasons[0]["episodes"][1]["name"] == "Half Loop"
    assert len(seasons[1]["episodes"]) == 1
