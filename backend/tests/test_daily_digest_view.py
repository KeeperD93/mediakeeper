"""The daily digest route: the remembered view, the public name of the viewer,
and when the redesigned blocks make the digest worth showing."""
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from constants.requests import REQUEST_AVAILABLE
from models.portal.news import News, NewsRead
from models.portal.request import MediaRequest
from services.portal import daily_digest as dd_svc
from services.portal import daily_digest_sources as sources
from services.portal._pseudo_words import generate_pseudo
from services.settings import get_user_preferences
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

VIEW_URL = "/api/portal/daily-digest/view"


@pytest.fixture
def quiet_sources():
    """The blocks older than the redesign show nothing, so each new one is judged alone."""
    dd_svc._digest_cache.clear()
    quota = {"used": 0, "max_allowed": 0, "unlimited": False, "remaining": 0}
    stubs = [
        patch.object(sources, "recent_adds", AsyncMock(return_value=[])),
        patch.object(sources, "upcoming_events", AsyncMock(return_value=[])),
        patch.object(sources, "ranking_snapshot", AsyncMock(
            return_value={"position": 0, "total": 0, "movement": 0, "top3": []},
        )),
        patch.object(sources, "quota_snapshot", AsyncMock(return_value=quota)),
        patch.object(sources, "open_tickets_count", AsyncMock(return_value=0)),
        patch.object(sources, "current_streak", AsyncMock(return_value=0)),
        patch.object(sources, "closest_achievement", AsyncMock(return_value=None)),
    ]
    for stub in stubs:
        stub.start()
    yield
    for stub in stubs:
        stub.stop()
    dd_svc._digest_cache.clear()


async def _sign_in(client, db, **profile):
    user, prof = await make_portal_user(db, username="alice_login", **profile)
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    return user, prof


async def _compact(client) -> bool:
    resp = await client.get("/api/portal/daily-digest")
    assert resp.status_code == 200, resp.text
    return resp.json()["compact"]


@pytest.mark.asyncio
async def test_the_picked_view_is_remembered(client, db_session, quiet_sources):
    await _sign_in(client, db_session)
    assert await _compact(client) is False  # the full view until one is picked

    for compact in (True, False):
        resp = await client.put(VIEW_URL, json={"compact": compact})
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"compact": compact}
        assert await _compact(client) is compact


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"compact": True, "extra": 1}, {}, {"compact": "maybe"}])
async def test_the_view_body_is_strict(client, db_session, body):
    await _sign_in(client, db_session)
    assert (await client.put(VIEW_URL, json=body)).status_code == 422


@pytest.mark.asyncio
async def test_a_dismissal_keeps_the_picked_view(client, db_session, quiet_sources):
    user, _ = await _sign_in(client, db_session)
    await client.put(VIEW_URL, json={"compact": True})
    assert (await client.post("/api/portal/daily-digest/dismiss")).status_code == 200

    prefs = json.loads((await get_user_preferences(db_session, user.id)).preferences)
    assert prefs["portal_daily_digest_compact"] is True
    assert "portal_daily_digest_dismissed_date" in prefs
    body = (await client.get("/api/portal/daily-digest")).json()
    assert (body["dismissed"], body["compact"]) == (True, True)


@pytest.mark.asyncio
async def test_the_view_needs_a_session(client):
    assert (await client.put(VIEW_URL, json={"compact": True})).status_code in (401, 403)


@pytest.mark.asyncio
async def test_the_view_is_capped_at_30_per_minute(client, db_session):
    await _sign_in(client, db_session)
    codes = [(await client.put(VIEW_URL, json={"compact": True})).status_code for _ in range(31)]
    assert codes[:30] == [200] * 30
    assert codes[30] == 429


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["fr", "en"])
async def test_the_greeting_never_shows_the_login(client, db_session, quiet_sources, locale):
    user, _ = await _sign_in(client, db_session, must_set=True)

    resp = await client.get("/api/portal/daily-digest", headers={"X-MK-Locale": locale})

    digest = resp.json()["digest"]
    assert digest["me"]["display_name"] == generate_pseudo(user.id, locale)
    assert "alice_login" not in json.dumps(digest)
    assert "display_name" not in digest and "avatar_url" not in digest


def _news() -> News:
    return News(title="Test news", content="Text", type="announcement", pinned=False, notify_discord=False)


async def _nothing(db, user, profile):
    return None


async def _read_news(db, user, profile):
    news = _news()
    db.add(news)
    await db.flush()
    db.add(NewsRead(news_id=news.id, user_id=user.id, dismissed=False))


async def _new_news(db, user, profile):
    db.add(_news())


async def _ending_access(db, user, profile):
    profile.access_end_date = datetime.now(UTC) + timedelta(days=3)


async def _available_request(db, user, profile):
    db.add(MediaRequest(
        user_id=user.id, tmdb_id=12345, media_type="movie", title="Test Movie",
        status=REQUEST_AVAILABLE, available_at=datetime.now(UTC) - timedelta(days=1),
    ))


@pytest.mark.asyncio
@pytest.mark.parametrize(("seed", "empty"), [
    (_nothing, True),
    (_read_news, True),
    (_new_news, False),
    (_ending_access, False),
    (_available_request, False),
])
async def test_the_new_blocks_count_as_content(db_session, quiet_sources, seed, empty):
    user, profile = await make_portal_user(db_session, username="alice")
    await seed(db_session, user, profile)
    await db_session.commit()

    digest = await dd_svc.build_digest(db_session, user, use_cache=False)

    assert digest["empty"] is empty
