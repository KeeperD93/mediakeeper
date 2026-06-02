"""Pydantic ``extra="forbid"`` contract on ``POST /api/portal/availability``.

Both ``AvailabilityItem`` and ``AvailabilityQuery`` declare
``model_config = ConfigDict(extra="forbid")`` so an unknown field in
the JSON body returns 422 instead of being silently ignored. Defense
in depth — a typo or a probing payload no longer slips past validation.
"""
from __future__ import annotations

import pytest

from services.portal.profiles import get_or_create_profile


@pytest.mark.asyncio
async def test_availability_rejects_extra_field_in_item(client, admin_user, db_session, portal_login):
    """An unknown field inside an ``AvailabilityItem`` returns 422."""
    await portal_login(client)
    await get_or_create_profile(db_session, admin_user)

    r = await client.post("/api/portal/availability", json={
        "items": [{"tmdb_id": 1, "media_type": "movie", "evil": "hack"}],
    })
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_availability_rejects_extra_field_in_query(client, admin_user, db_session, portal_login):
    """An unknown field at the ``AvailabilityQuery`` root returns 422."""
    await portal_login(client)
    await get_or_create_profile(db_session, admin_user)

    r = await client.post("/api/portal/availability", json={
        "items": [{"tmdb_id": 1, "media_type": "movie"}],
        "evil": "hack",
    })
    assert r.status_code == 422, r.text
