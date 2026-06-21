"""Tests for /api/portal/changelog."""

import pytest
from pydantic import ValidationError

from api.portal_changelog import (
    PORTAL_VERSION,
    MarkSeenRequest,
    _has_entries,
    _parse_changelog,
)
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


def test_mark_seen_request_rejects_extra_key():
    """extra=forbid: an unknown body field fails validation loudly (symmetry
    with the admin MarkSeenRequest twin)."""
    with pytest.raises(ValidationError) as exc:
        MarkSeenRequest.model_validate({"version": "1.0.0", "bogus_field": True})
    assert "bogus_field" in str(exc.value)


@pytest.mark.asyncio
async def test_mark_seen_endpoint_returns_422_on_extra_key(client, db_session):
    """Round-trip: the extra=forbid rejection surfaces as a clean 422, not
    shadowed by the portal auth gate."""
    await _seed_portal_viewer(client, db_session)
    resp = await client.post(
        "/api/portal/changelog/seen",
        json={"version": "1.0.0", "rogue_probe": "x"},
    )
    assert resp.status_code == 422, resp.text
    assert "rogue_probe" in str(resp.json())


@pytest.mark.asyncio
async def test_changelog_list_requires_auth(client):
    """GET /api/portal/changelog/ must reject unauthenticated requests."""
    resp = await client.get("/api/portal/changelog/")
    assert resp.status_code in (401, 403)


def test_has_entries_detects_empty_versions():
    assert _has_entries({"categories": {"Added": ["x"]}}) is True
    assert _has_entries({"categories": {}}) is False
    assert _has_entries({"categories": {"Added": []}}) is False  # header, no items


# [Unreleased] is dropped (no date); 9.9.8 has no categories; 9.9.6 has an
# empty category header — only 9.9.9 and 9.9.7 carry real entries.
_SAMPLE = """## [Unreleased]

### Added
- unreleased item

## [9.9.9] - 2026-01-03

### Added
- Real feature.

## [9.9.8] - 2026-01-02

## [9.9.7] - 2026-01-01

### Fixed
- Real fix.

## [9.9.6] - 2025-12-31

### Added
"""


def test_parser_skips_empty_versions(monkeypatch, tmp_path):
    f = tmp_path / "CHANGELOG_PORTAL_FR.md"
    f.write_text(_SAMPLE, encoding="utf-8")
    monkeypatch.setattr("api.portal_changelog._find_changelog", lambda lang="fr": f)
    versions = _parse_changelog(lang="fr")
    assert [v["version"] for v in versions] == ["9.9.9", "9.9.7"]
    assert versions[0]["categories"] == {"Added": ["Real feature."]}


def test_parser_limit_counts_only_non_empty(monkeypatch, tmp_path):
    f = tmp_path / "CHANGELOG_PORTAL_FR.md"
    f.write_text(_SAMPLE, encoding="utf-8")
    monkeypatch.setattr("api.portal_changelog._find_changelog", lambda lang="fr": f)
    versions = _parse_changelog(lang="fr", max_versions=1)
    assert [v["version"] for v in versions] == ["9.9.9"]


def test_find_changelog_coerces_unknown_lang_to_fr():
    """Portal twin of #391 — unsupported lang falls back to "fr"."""
    from api.portal_changelog import _find_changelog

    assert _find_changelog("../../etc/passwd") == _find_changelog("fr")
    assert _find_changelog("zz") == _find_changelog("fr")
