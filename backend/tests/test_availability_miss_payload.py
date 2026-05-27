"""Miss-payload contract on ``POST /api/portal/availability``.

When a tmdb_id has no row in ``EmbyTmdbIndex`` (typical for freshly
added Emby items where the indexer hasn't caught up yet), the route
must return an explicit ``null`` under that key — not an all-null
object like ``{availability:null, emby_item_id:null, emby_url:null}``.

The frontend cache uses the bare null to flag the entry as
``_empty``, which lets ``MediaCard`` fall back to the inline
``availability:"full"`` hint stamped by ``/library/recent`` while
the index catches up. A truthy "phantom hit" object would silently
erase that fallback and make the "Dispo" badge flicker for ~0.5 s
on page load before disappearing.
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
async def test_unknown_tmdb_id_returns_null_under_key(
    client, admin_user, db_session,
):
    """Unindexed tmdb_id → ``results[id]`` is exactly ``None``.

    Pinning the contract so a future change can't silently revert to
    an all-null object (which the frontend cache mis-classifies as a
    real hit).
    """
    await _portal_login(client)
    await get_or_create_profile(db_session, admin_user)

    r = await client.post("/api/portal/availability", json={
        "items": [{"tmdb_id": 999999999, "media_type": "movie"}],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["results"] == {"999999999": None}
