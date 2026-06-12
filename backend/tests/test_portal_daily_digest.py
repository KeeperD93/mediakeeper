"""Tests for /api/portal/daily-digest."""
import json
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import patch, AsyncMock

from core.security import create_access_token, hash_password
from models.user import User
from models.portal.profile import UserProfile
from services.portal import daily_digest as dd_svc
from services.portal import daily_digest_sources as dd_sources
from services.portal.xp import MAX_LEVEL, xp_for_level
from services.settings import get_user_preferences, upsert_user_preferences


async def _seed_viewer(client, db_session, username: str = "viewer_digest"):
    user = User(
        username=username,
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
    )
    db_session.add(profile)
    await db_session.commit()

    token = create_access_token({"sub": username, "scope": "portal"})
    client.cookies.set("rq_token", token)
    return user


def _stub_all_digest_sources():
    """Patch every expensive aggregator so the digest call is pure.

    Each aggregator is independently network/DB-heavy; the digest logic
    we want to cover is orchestration, caching, and dismissal — not the
    leaf data fetching (exercised by their own tests).
    """
    return [
        patch.object(dd_sources, "recent_adds", AsyncMock(return_value=[])),
        patch.object(dd_sources, "upcoming_events", AsyncMock(return_value=[])),
        patch.object(dd_sources, "ranking_snapshot", AsyncMock(return_value={"position": 0, "total": 0, "movement": 0, "top3": []})),
        patch.object(dd_sources, "quota_snapshot", AsyncMock(return_value={"used": 0, "max_allowed": 0, "unlimited": False, "remaining": 0})),
        patch.object(dd_sources, "open_tickets_count", AsyncMock(return_value=0)),
        patch.object(dd_sources, "current_streak", AsyncMock(return_value=0)),
        patch.object(dd_sources, "closest_achievement", AsyncMock(return_value=None)),
    ]


@pytest.mark.asyncio
async def test_digest_empty_when_no_data(client, db_session):
    """With every source empty, digest.empty must be true and dismissed false."""
    await _seed_viewer(client, db_session)
    dd_svc._digest_cache.clear()

    stubs = _stub_all_digest_sources()
    for s in stubs: s.start()
    try:
        resp = await client.get("/api/portal/daily-digest")
    finally:
        for s in stubs: s.stop()

    assert resp.status_code == 200
    data = resp.json()
    assert data["dismissed"] is False
    assert data["digest"]["empty"] is True


@pytest.mark.asyncio
async def test_digest_not_empty_when_content(client, db_session):
    """A streak alone should be enough to flip empty=false."""
    await _seed_viewer(client, db_session)
    dd_svc._digest_cache.clear()

    stubs = _stub_all_digest_sources()
    # Override streak to 3 consecutive days
    stubs[5] = patch.object(dd_sources, "current_streak", AsyncMock(return_value=3))
    for s in stubs: s.start()
    try:
        resp = await client.get("/api/portal/daily-digest")
    finally:
        for s in stubs: s.stop()

    data = resp.json()
    assert data["digest"]["empty"] is False
    assert data["digest"]["streak"] == 3


@pytest.mark.asyncio
async def test_dismiss_then_get_reports_dismissed(client, db_session):
    """POST /dismiss must flip dismissed=true for the rest of the day."""
    user = await _seed_viewer(client, db_session)
    dd_svc._digest_cache.clear()

    resp = await client.post("/api/portal/daily-digest/dismiss")
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    prefs = await get_user_preferences(db_session, user.id)
    stored = json.loads(prefs.preferences)
    assert "portal_daily_digest_dismissed_date" in stored

    stubs = _stub_all_digest_sources()
    for s in stubs: s.start()
    try:
        resp = await client.get("/api/portal/daily-digest")
    finally:
        for s in stubs: s.stop()

    assert resp.json()["dismissed"] is True


@pytest.mark.asyncio
async def test_cache_hit_avoids_rebuild(client, db_session):
    """A second call within the TTL must not re-invoke the aggregators."""
    await _seed_viewer(client, db_session)
    dd_svc._digest_cache.clear()

    recent_stub = AsyncMock(return_value=[])
    stubs = _stub_all_digest_sources()
    stubs[0] = patch.object(dd_sources, "recent_adds", recent_stub)
    for s in stubs: s.start()
    try:
        await client.get("/api/portal/daily-digest")
        await client.get("/api/portal/daily-digest")
    finally:
        for s in stubs: s.stop()

    # Aggregator called exactly once across two HTTP calls thanks to cache.
    assert recent_stub.await_count == 1


@pytest.mark.asyncio
async def test_force_bypasses_cache(client, db_session):
    """?force=true rebuilds even when cached."""
    await _seed_viewer(client, db_session)
    dd_svc._digest_cache.clear()

    recent_stub = AsyncMock(return_value=[])
    stubs = _stub_all_digest_sources()
    stubs[0] = patch.object(dd_sources, "recent_adds", recent_stub)
    for s in stubs: s.start()
    try:
        await client.get("/api/portal/daily-digest")
        await client.get("/api/portal/daily-digest?force=true")
    finally:
        for s in stubs: s.stop()

    assert recent_stub.await_count == 2


@pytest.mark.asyncio
async def test_endpoints_require_auth(client):
    """Without rq_token the endpoints must reject."""
    resp = await client.get("/api/portal/daily-digest")
    assert resp.status_code in (401, 403)
    resp = await client.post("/api/portal/daily-digest/dismiss")
    assert resp.status_code in (401, 403)


def test_level_info_below_max_progresses_to_next():
    """A mid-level profile reports progress toward the next level."""
    floor, ceiling = xp_for_level(5), xp_for_level(6)
    profile = UserProfile(level=5, xp=floor + (ceiling - floor) // 2)
    info = dd_sources.level_info(profile)
    assert info["maxed"] is False
    assert info["xp_next_level"] == ceiling
    assert 40 <= info["percent"] <= 60


def test_level_info_at_max_level_is_full_and_capped():
    """At the cap the bar is full and there is no phantom level 51."""
    profile = UserProfile(level=MAX_LEVEL, xp=xp_for_level(MAX_LEVEL) + 1490)
    info = dd_sources.level_info(profile)
    assert info["maxed"] is True
    assert info["percent"] == 100
    assert info["xp_next_level"] == info["xp_current_level"] == xp_for_level(MAX_LEVEL)


def _fake_adds(count: int) -> list[dict]:
    """``count`` items dated day-0..day-(count-1), newest first (Emby DESC)."""
    today = datetime.now(timezone.utc).date()
    return [
        {
            "tmdb_id": i, "emby_item_id": str(i), "title": f"T{i}", "year": "2024",
            "media_type": "movie", "poster_url": "",
            "date_created": (today - timedelta(days=i)).isoformat(),
        }
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_recent_adds_keeps_only_items_after_since(db_session):
    """Items strictly newer than the since-date are kept, older ones dropped."""
    since = datetime.now(timezone.utc) - timedelta(days=10)
    with patch.object(dd_sources, "get_recently_added", AsyncMock(return_value=_fake_adds(40))):
        out = await dd_sources.recent_adds(db_session, since=since)
    # since.date() == today-10; strict ">" keeps days 0..9 only.
    assert [it["tmdb_id"] for it in out] == list(range(10))
    assert all("backdrop_url" not in it for it in out)  # dead field dropped


@pytest.mark.asyncio
async def test_recent_adds_caps_at_30(db_session):
    """A long catch-up window is capped at 30 posters, newest first."""
    since = datetime.now(timezone.utc) - timedelta(days=100)
    with patch.object(dd_sources, "get_recently_added", AsyncMock(return_value=_fake_adds(40))):
        out = await dd_sources.recent_adds(db_session, since=since)
    assert [it["tmdb_id"] for it in out] == list(range(30))


@pytest.mark.asyncio
async def test_dismiss_stores_dismissed_at_instant(client, db_session):
    """Dismiss records the precise instant so the 24h grace can be timed."""
    user = await _seed_viewer(client, db_session, username="viewer_digest_at")
    dd_svc._digest_cache.clear()
    await client.post("/api/portal/daily-digest/dismiss")
    stored = json.loads((await get_user_preferences(db_session, user.id)).preferences)
    assert "portal_daily_digest_dismissed_at" in stored


def test_recent_cutoff_uses_dismiss_after_grace():
    """Past the 24h grace, the dismiss instant becomes the cutoff watermark."""
    now = datetime.now(timezone.utc)
    dismissed_at = now - timedelta(hours=25)
    cutoff = dd_svc._recent_cutoff(
        {"portal_daily_digest_dismissed_at": dismissed_at.isoformat()}, now
    )
    assert abs((cutoff - dismissed_at).total_seconds()) < 2


def test_recent_cutoff_holds_at_floor_within_grace():
    """Within the 24h grace, no committed watermark → cutoff floors at 30 days."""
    now = datetime.now(timezone.utc)
    dismissed_at = now - timedelta(hours=2)
    cutoff = dd_svc._recent_cutoff(
        {"portal_daily_digest_dismissed_at": dismissed_at.isoformat()}, now
    )
    floor = now - timedelta(days=dd_svc._MAX_LOOKBACK_DAYS)
    assert abs((cutoff - floor).total_seconds()) < 2


def test_recent_cutoff_ignores_future_watermark():
    """A corrupted future seen_at must not blackout the list (falls to floor)."""
    now = datetime.now(timezone.utc)
    cutoff = dd_svc._recent_cutoff(
        {"portal_daily_digest_recent_seen_at": (now + timedelta(days=5)).isoformat()}, now
    )
    floor = now - timedelta(days=dd_svc._MAX_LOOKBACK_DAYS)
    assert abs((cutoff - floor).total_seconds()) < 2


@pytest.mark.asyncio
async def test_dismiss_commits_elapsed_watermark(db_session):
    """A fresh dismiss promotes a prior, grace-elapsed dismiss into the watermark."""
    user = User(
        username="viewer_promote",
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    old = datetime.now(timezone.utc) - timedelta(hours=30)
    await upsert_user_preferences(
        db_session, user.id,
        preferences=json.dumps({"portal_daily_digest_dismissed_at": old.isoformat()}),
    )
    await dd_svc.mark_dismissed(db_session, user.id)
    prefs = await dd_svc._load_prefs(db_session, user.id)
    assert dd_svc._parse_dt(prefs["portal_daily_digest_recent_seen_at"]) == old
    assert dd_svc._parse_dt(prefs["portal_daily_digest_dismissed_at"]) != old
