"""Tests for /api/portal/daily-digest."""
import json

import pytest
from unittest.mock import patch, AsyncMock

from core.security import create_access_token, hash_password
from models.user import User
from models.portal.profile import UserProfile
from services.portal import daily_digest as dd_svc
from services.portal import daily_digest_sources as dd_sources
from services.settings import get_user_preferences


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
