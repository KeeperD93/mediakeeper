"""The new Portal version in the daily digest: shown a week from the first close
under it, marked new until the viewer opens it, and worth opening the digest for."""
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from api import portal_changelog
from constants.changelog import PORTAL_SEEN_VERSION_KEY
from constants.daily_digest import RELEASE_SHOWN_DAYS
from services.portal import daily_digest as dd_svc
from services.portal import daily_digest_sources as sources
from services.settings import get_user_preferences, upsert_user_preferences
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

DIGEST_URL = "/api/portal/daily-digest"
RELEASE = {
    "version": "1.2.3",
    "date": "2026-11-13",
    "categories": {"Changed": ["Test change"], "Fixed": ["Test fix one", "Test fix two"]},
}


@pytest.fixture
def quiet_sources():
    """Every other block is empty, so the version is judged alone."""
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
        patch.object(portal_changelog, "latest_release", return_value=RELEASE),
        patch.object(portal_changelog, "PORTAL_VERSION", RELEASE["version"]),
    ]
    for stub in stubs:
        stub.start()
    yield
    for stub in stubs:
        stub.stop()
    dd_svc._digest_cache.clear()


def _week_started(days_ago: float, version: str = RELEASE["version"]) -> dict:
    since = datetime.now(UTC) - timedelta(days=days_ago)
    return {"portal_daily_digest_release": {"version": version, "since": since.isoformat()}}


def test_a_new_version_shows_marked_new_until_opened():
    now = datetime.now(UTC)
    block = dd_svc._release_block(RELEASE, {}, now)
    assert block == {**RELEASE, "is_new": True}

    opened = dd_svc._release_block(RELEASE, {PORTAL_SEEN_VERSION_KEY: "1.2.3"}, now)
    assert opened["is_new"] is False


@pytest.mark.parametrize(("days_ago", "shown"), [
    (0, True),
    (RELEASE_SHOWN_DAYS - 0.01, True),
    (RELEASE_SHOWN_DAYS, False),
    (RELEASE_SHOWN_DAYS + 30, False),
])
def test_the_version_stays_a_week_from_the_first_close(days_ago, shown):
    block = dd_svc._release_block(RELEASE, _week_started(days_ago), datetime.now(UTC))
    assert (block is not None) is shown


def test_the_week_of_an_older_version_does_not_hide_the_new_one():
    prefs = _week_started(RELEASE_SHOWN_DAYS + 30, version="1.2.2")
    assert dd_svc._release_block(RELEASE, prefs, datetime.now(UTC)) is not None


@pytest.mark.parametrize("record", ["1.2.3", {"version": "1.2.3", "since": "not a date"}, {}])
def test_an_unreadable_week_start_keeps_the_version_shown(record):
    prefs = {"portal_daily_digest_release": record}
    assert dd_svc._release_block(RELEASE, prefs, datetime.now(UTC)) is not None


def test_no_dated_version_means_no_block():
    assert dd_svc._release_block(None, {}, datetime.now(UTC)) is None


@pytest.mark.asyncio
async def test_the_first_close_starts_the_week_and_later_ones_keep_it(db_session):
    user, _ = await make_portal_user(db_session, username="alice")

    await dd_svc.mark_dismissed(db_session, user.id, release_version="1.2.3")
    first = (await dd_svc._load_prefs(db_session, user.id))["portal_daily_digest_release"]
    await dd_svc.mark_dismissed(db_session, user.id, release_version="1.2.3")
    second = (await dd_svc._load_prefs(db_session, user.id))["portal_daily_digest_release"]

    assert first["version"] == "1.2.3"
    assert second == first


@pytest.mark.asyncio
async def test_a_newer_version_restarts_the_week(db_session):
    user, _ = await make_portal_user(db_session, username="alice")
    await upsert_user_preferences(
        db_session, user.id, preferences=json.dumps(_week_started(20, version="1.2.2")),
    )

    await dd_svc.mark_dismissed(db_session, user.id, release_version="1.2.3")

    record = (await dd_svc._load_prefs(db_session, user.id))["portal_daily_digest_release"]
    assert record["version"] == "1.2.3"
    assert datetime.now(UTC) - dd_svc._parse_dt(record["since"]) < timedelta(minutes=1)


@pytest.mark.asyncio
async def test_a_new_version_alone_opens_the_digest(db_session, quiet_sources):
    user, _ = await make_portal_user(db_session, username="alice")

    digest = await dd_svc.build_digest(db_session, user, use_cache=False, release=RELEASE)
    assert digest["release"]["is_new"] is True
    assert digest["empty"] is False

    await upsert_user_preferences(
        db_session, user.id, preferences=json.dumps({PORTAL_SEEN_VERSION_KEY: "1.2.3"}),
    )
    digest = await dd_svc.build_digest(db_session, user, use_cache=False, release=RELEASE)
    assert digest["release"]["is_new"] is False
    assert digest["empty"] is True


@pytest.mark.asyncio
async def test_opening_the_version_refreshes_the_cached_digest(client, db_session, quiet_sources):
    user, _ = await make_portal_user(db_session, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    before = (await client.get(DIGEST_URL)).json()["digest"]
    seen = await client.post("/api/portal/changelog/seen", json={"version": "1.2.3"})
    after = (await client.get(DIGEST_URL)).json()["digest"]

    assert seen.status_code == 200, seen.text
    assert before["release"]["version"] == "1.2.3"
    assert (before["release"]["is_new"], after["release"]["is_new"]) == (True, False)


@pytest.mark.asyncio
async def test_closing_the_digest_starts_the_week_of_the_current_version(
    client, db_session, quiet_sources,
):
    user, _ = await make_portal_user(db_session, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    assert (await client.post(f"{DIGEST_URL}/dismiss")).status_code == 200

    prefs = json.loads((await get_user_preferences(db_session, user.id)).preferences)
    assert prefs["portal_daily_digest_release"]["version"] == "1.2.3"


def test_the_release_is_the_dated_current_version():
    release = portal_changelog.latest_release("fr")
    assert release is not None
    assert release["version"] == portal_changelog.PORTAL_VERSION
    assert any(release["categories"].values())


def test_an_undated_current_version_has_no_release():
    with patch.object(portal_changelog, "PORTAL_VERSION", "9.9.9"):
        assert portal_changelog.latest_release("en") is None
