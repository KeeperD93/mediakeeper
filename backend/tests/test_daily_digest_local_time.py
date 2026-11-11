"""« Quoi de neuf aujourd'hui ? » comes back at midnight in the saved zone."""
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from models.portal.profile import UserProfile
from models.user import User
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.portal import daily_digest as digest
from services.portal import daily_digest_sources as sources
from services.settings import get_user_preferences, set_setting
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

# Tuesday in Paris until 23:00 UTC; Tuesday in UTC until the next midnight.
TUESDAY_NIGHT_IN_PARIS = datetime(2026, 11, 3, 22, 30, tzinfo=UTC)
WEDNESDAY_IN_PARIS = datetime(2026, 11, 3, 23, 10, tzinfo=UTC)


def _freeze(monkeypatch, moment: datetime) -> None:
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment

    monkeypatch.setattr(digest, "datetime", _Frozen)


async def _viewer(db) -> tuple[User, UserProfile]:
    return await make_portal_user(db, username="alice")


def _stubbed_sources() -> list:
    empty = {"position": 0, "total": 0, "movement": 0, "top3": []}
    quota = {"used": 0, "max_allowed": 0, "unlimited": False, "remaining": 0}
    return [
        patch.object(sources, "recent_adds", AsyncMock(return_value=[])),
        patch.object(sources, "upcoming_events", AsyncMock(return_value=[])),
        patch.object(sources, "ranking_snapshot", AsyncMock(return_value=empty)),
        patch.object(sources, "quota_snapshot", AsyncMock(return_value=quota)),
        patch.object(sources, "open_tickets_count", AsyncMock(return_value=0)),
        patch.object(sources, "current_streak", AsyncMock(return_value=0)),
        patch.object(sources, "closest_achievement", AsyncMock(return_value=None)),
    ]


@pytest.fixture
def stubbed_sources():
    digest._digest_cache.clear()
    stubs = _stubbed_sources()
    for stub in stubs:
        stub.start()
    yield
    for stub in stubs:
        stub.stop()
    digest._digest_cache.clear()


@pytest.mark.asyncio
async def test_a_dismissal_lasts_until_midnight_in_the_saved_zone(db_session, monkeypatch):
    alice, _ = await _viewer(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")

    _freeze(monkeypatch, TUESDAY_NIGHT_IN_PARIS)
    assert await digest.mark_dismissed(db_session, alice.id) == "2026-11-03"
    assert await digest.is_dismissed_today(db_session, alice.id) is True

    # The same day in UTC, the next one in Paris.
    _freeze(monkeypatch, WEDNESDAY_IN_PARIS)
    assert await digest.is_dismissed_today(db_session, alice.id) is False


@pytest.mark.asyncio
async def test_a_dismissal_after_midnight_lasts_the_whole_local_day(db_session, monkeypatch):
    alice, _ = await _viewer(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")

    _freeze(monkeypatch, WEDNESDAY_IN_PARIS)
    assert await digest.mark_dismissed(db_session, alice.id) == "2026-11-04"

    # Tomorrow in UTC, 23:59 on the same Wednesday in Paris.
    _freeze(monkeypatch, datetime(2026, 11, 4, 22, 59, tzinfo=UTC))
    assert await digest.is_dismissed_today(db_session, alice.id) is True

    _freeze(monkeypatch, datetime(2026, 11, 4, 23, tzinfo=UTC))
    assert await digest.is_dismissed_today(db_session, alice.id) is False


@pytest.mark.asyncio
async def test_without_a_zone_the_day_changes_at_midnight_utc(db_session, monkeypatch):
    alice, _ = await _viewer(db_session)

    _freeze(monkeypatch, TUESDAY_NIGHT_IN_PARIS)
    assert await digest.mark_dismissed(db_session, alice.id) == "2026-11-03"

    _freeze(monkeypatch, WEDNESDAY_IN_PARIS)
    assert await digest.is_dismissed_today(db_session, alice.id) is True

    _freeze(monkeypatch, datetime(2026, 11, 4, 0, tzinfo=UTC))
    assert await digest.is_dismissed_today(db_session, alice.id) is False


@pytest.mark.asyncio
async def test_the_instant_of_a_dismissal_stays_in_utc(db_session, monkeypatch):
    """The 24 hour grace after a dismissal is a duration: only the date follows the zone."""
    alice, _ = await _viewer(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    _freeze(monkeypatch, WEDNESDAY_IN_PARIS)

    await digest.mark_dismissed(db_session, alice.id)

    row = await get_user_preferences(db_session, alice.id)
    prefs = json.loads(row.preferences)
    assert prefs["portal_daily_digest_dismissed_date"] == "2026-11-04"
    assert prefs["portal_daily_digest_dismissed_at"] == WEDNESDAY_IN_PARIS.isoformat()


@pytest.mark.asyncio
async def test_the_payload_is_dated_in_the_saved_zone(db_session, monkeypatch, stubbed_sources):
    alice, _ = await _viewer(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    _freeze(monkeypatch, WEDNESDAY_IN_PARIS)

    payload = await digest.build_digest(db_session, alice)

    assert payload["date"] == "2026-11-04"


@pytest.mark.asyncio
async def test_the_cache_of_one_local_day_is_not_served_the_next(
    db_session, monkeypatch, stubbed_sources,
):
    alice, _ = await _viewer(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")

    _freeze(monkeypatch, TUESDAY_NIGHT_IN_PARIS)
    tuesday = await digest.build_digest(db_session, alice)
    assert await digest.build_digest(db_session, alice) is tuesday

    # Forty minutes later, within the cache hour, it is Wednesday in Paris.
    _freeze(monkeypatch, TUESDAY_NIGHT_IN_PARIS + timedelta(minutes=40))
    wednesday = await digest.build_digest(db_session, alice)

    assert (tuesday["date"], wednesday["date"]) == ("2026-11-03", "2026-11-04")


@pytest.mark.asyncio
async def test_the_routes_follow_the_saved_zone(client, db_session, monkeypatch, stubbed_sources):
    alice, _ = await _viewer(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    client.cookies.set(PORTAL_COOKIE, portal_token(alice.username))

    _freeze(monkeypatch, TUESDAY_NIGHT_IN_PARIS)
    dismissed = await client.post("/api/portal/daily-digest/dismiss", json={})
    assert dismissed.json() == {"success": True, "date": "2026-11-03"}
    assert (await client.get("/api/portal/daily-digest")).json()["dismissed"] is True

    _freeze(monkeypatch, WEDNESDAY_IN_PARIS)
    body = (await client.get("/api/portal/daily-digest")).json()
    assert body["dismissed"] is False
    assert body["digest"]["date"] == "2026-11-04"
