"""Pydantic coercion contract on ``POST /api/portal/availability``.

Background — production hit a 500 because the route accepted
``items: list[dict]`` and the frontend occasionally shipped
``tmdb_id`` as a string. ``EmbyTmdbIndex.tmdb_id`` is a strict
``Integer`` column, so asyncpg refused the parameter binding with a
``DataError`` and FastAPI surfaced it as 500.

Typing the payload as ``list[AvailabilityItem]`` lets Pydantic v2
coerce numeric strings into ``int`` and reject everything else with
a clean 422 — neither path can reach the SQL layer with a malformed
``tmdb_id`` again.
"""
from __future__ import annotations

import pytest

from services.portal.profiles import get_or_create_profile


async def _portal_login(client) -> None:
    r = await client.post("/api/auth/portal-login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_availability_accepts_int_tmdb_id(client, admin_user, db_session):
    """Backwards-compatible payload — frontend sends int. The endpoint
    returns 200 with the (empty) results map for an unknown id."""
    await _portal_login(client)
    await get_or_create_profile(db_session, admin_user)

    r = await client.post("/api/portal/availability", json={
        "items": [{"tmdb_id": 162617, "media_type": "movie"}],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "results" in body
    assert "162617" in body["results"]


@pytest.mark.asyncio
async def test_availability_accepts_string_tmdb_id(client, admin_user, db_session):
    """Pydantic v2 coerces a numeric string to int — the production
    payload that triggered the original 500 must now succeed."""
    await _portal_login(client)
    await get_or_create_profile(db_session, admin_user)

    r = await client.post("/api/portal/availability", json={
        "items": [{"tmdb_id": "162617", "media_type": "movie"}],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "results" in body
    assert "162617" in body["results"]


@pytest.mark.asyncio
async def test_availability_rejects_non_numeric_tmdb_id(client, admin_user, db_session):
    """Anything that isn't a base-10 integer fails Pydantic validation
    and surfaces as 422 instead of 500. No SQL is issued."""
    await _portal_login(client)
    await get_or_create_profile(db_session, admin_user)

    r = await client.post("/api/portal/availability", json={
        "items": [{"tmdb_id": "abc", "media_type": "movie"}],
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_availability_rejects_invalid_media_type(client, admin_user, db_session):
    """``media_type`` is constrained to ``movie`` / ``tv`` so a typo
    like ``"film"`` cannot reach the completeness branch."""
    await _portal_login(client)
    await get_or_create_profile(db_session, admin_user)

    r = await client.post("/api/portal/availability", json={
        "items": [{"tmdb_id": 1, "media_type": "film"}],
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_availability_handles_empty_items(client, admin_user, db_session):
    """Empty payload is a no-op — returns 200 with an empty results map."""
    await _portal_login(client)
    await get_or_create_profile(db_session, admin_user)

    r = await client.post("/api/portal/availability", json={"items": []})
    assert r.status_code == 200
    assert r.json() == {"results": {}}
