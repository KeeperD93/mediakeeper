"""Tests for the /api/changelog/combined endpoints.

These routes merge the admin changelog with the Portal changelog so the
admin sees both surfaces in a single timeline + modal. Each test exercises
one of the three new sub-routes plus the shared `_merge_changelogs` helper.
"""
from __future__ import annotations

import pytest

from api.changelog import APP_VERSION, _merge_changelogs
from api.portal_changelog import PORTAL_VERSION


async def _login_admin(client, monkeypatch) -> None:
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "TestPassword123!"},
    )
    assert resp.status_code == 200, resp.text


def test_merge_keeps_both_surfaces_when_same_version():
    """A version present in both files exposes admin AND portal categories."""
    admin = [
        {
            "version": "1.0.0",
            "date": "2026-05-21",
            "categories": {"Added": ["admin feature"]},
        }
    ]
    portal = [
        {
            "version": "1.0.0",
            "date": "2026-05-21",
            "categories": {"Fixed": ["portal bug"]},
        }
    ]
    merged = _merge_changelogs(admin, portal)
    assert len(merged) == 1
    entry = merged[0]
    assert entry["version"] == "1.0.0"
    assert entry["admin"] == {"Added": ["admin feature"]}
    assert entry["portal"] == {"Fixed": ["portal bug"]}


def test_merge_marks_missing_surface_as_none():
    """A version only in one file gets ``None`` on the other surface."""
    admin = [
        {
            "version": "0.9.9",
            "date": "2026-05-13",
            "categories": {"Added": ["admin only"]},
        }
    ]
    portal = [
        {
            "version": "0.3.0",
            "date": "2026-05-13",
            "categories": {"Added": ["portal only"]},
        }
    ]
    merged = _merge_changelogs(admin, portal)
    versions = {e["version"]: e for e in merged}
    assert versions["0.9.9"]["admin"] == {"Added": ["admin only"]}
    assert versions["0.9.9"]["portal"] is None
    assert versions["0.3.0"]["admin"] is None
    assert versions["0.3.0"]["portal"] == {"Added": ["portal only"]}


def test_merge_sorts_by_date_descending():
    """Most recent entries come first regardless of which surface owns them."""
    admin = [
        {"version": "0.9.9", "date": "2026-05-13", "categories": {}},
        {"version": "1.0.0", "date": "2026-05-21", "categories": {}},
    ]
    portal = [
        {"version": "0.4.0", "date": "2026-05-18", "categories": {}},
    ]
    merged = _merge_changelogs(admin, portal)
    dates = [e["date"] for e in merged]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_combined_requires_auth(client):
    """GET /api/changelog/combined must reject unauthenticated requests."""
    resp = await client.get("/api/changelog/combined")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_combined_returns_both_versions(client, admin_user, monkeypatch):
    """The endpoint exposes the current app + portal version markers."""
    await _login_admin(client, monkeypatch)

    resp = await client.get("/api/changelog/combined")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["app_version"] == APP_VERSION
    assert payload["portal_version"] == PORTAL_VERSION
    assert isinstance(payload["versions"], list)


@pytest.mark.asyncio
async def test_combined_limit_clamps_result(client, admin_user, monkeypatch):
    """The `limit` query param caps the merged version count."""
    await _login_admin(client, monkeypatch)

    resp = await client.get("/api/changelog/combined?limit=1")
    assert resp.status_code == 200
    assert len(resp.json()["versions"]) <= 1


@pytest.mark.asyncio
async def test_combined_check_reports_fresh_admin(client, admin_user, monkeypatch):
    """A user who never dismissed the modal sees has_any_new=True."""
    await _login_admin(client, monkeypatch)

    resp = await client.get("/api/changelog/combined/check")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["app_version"] == APP_VERSION
    assert payload["portal_version"] == PORTAL_VERSION
    assert payload["admin_seen"] == ""
    assert payload["portal_seen"] == ""
    assert payload["admin_has_new"] is True
    assert payload["portal_has_new"] is True
    assert payload["has_any_new"] is True


@pytest.mark.asyncio
async def test_combined_seen_marks_both_versions(client, admin_user, monkeypatch):
    """POST /seen records both seen-version markers in one call."""
    await _login_admin(client, monkeypatch)

    resp = await client.post("/api/changelog/combined/seen", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["app_version"] == APP_VERSION
    assert body["portal_version"] == PORTAL_VERSION

    resp = await client.get("/api/changelog/combined/check")
    payload = resp.json()
    assert payload["admin_seen"] == APP_VERSION
    assert payload["portal_seen"] == PORTAL_VERSION
    assert payload["has_any_new"] is False


@pytest.mark.asyncio
async def test_combined_seen_rejects_extra_fields(client, admin_user, monkeypatch):
    """The Pydantic schema has ``extra='forbid'`` — unknown keys must 422."""
    await _login_admin(client, monkeypatch)

    resp = await client.post(
        "/api/changelog/combined/seen",
        json={"unknown_field": "x"},
    )
    assert resp.status_code == 422
