"""Tests for /api/portal/changelog."""

import pytest

from api.portal_changelog import PORTAL_VERSION, _parse_changelog
from core.security import create_access_token, hash_password
from models.user import User
from models.portal.profile import UserProfile


@pytest.mark.asyncio
async def test_current_version_is_exposed(client):
    """GET /api/portal/changelog/current must return the Demandes version."""
    resp = await client.get("/api/portal/changelog/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == PORTAL_VERSION


@pytest.mark.asyncio
async def test_parser_reads_the_shipped_changelog():
    """The shipped CHANGELOG_PORTAL_FR.md must parse without crashing.

    The file may only contain [Unreleased] (which the parser filters out
    because it has no date), so we just assert the call returns a list.
    """
    versions = _parse_changelog(lang="fr")
    assert isinstance(versions, list)


async def _seed_portal_viewer(client, db_session, username: str = "viewer_portal"):
    """Create a user + portal profile and attach a Portal-scoped token."""
    user = User(
        username=username,
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    db_session.add(UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        account_active=True,
    ))
    await db_session.commit()

    token = create_access_token({"sub": username, "scope": "portal"})
    client.cookies.set("rq_token", token)


@pytest.mark.asyncio
async def test_check_returns_has_new_for_fresh_user(client, db_session):
    """A viewer who never dismissed the modal must see has_new=True."""
    await _seed_portal_viewer(client, db_session)

    resp = await client.get("/api/portal/changelog/check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_version"] == PORTAL_VERSION
    assert data["seen_version"] == ""
    assert data["has_new"] is True


@pytest.mark.asyncio
async def test_mark_seen_then_check(client, db_session):
    """After /seen, /check must report has_new=False."""
    await _seed_portal_viewer(client, db_session)

    resp = await client.post("/api/portal/changelog/seen", json={})
    assert resp.status_code == 200
    assert resp.json()["version"] == PORTAL_VERSION

    resp = await client.get("/api/portal/changelog/check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["seen_version"] == PORTAL_VERSION
    assert data["has_new"] is False


@pytest.mark.asyncio
async def test_changelog_list_requires_auth(client):
    """GET /api/portal/changelog/ must reject unauthenticated requests."""
    resp = await client.get("/api/portal/changelog/")
    assert resp.status_code in (401, 403)
