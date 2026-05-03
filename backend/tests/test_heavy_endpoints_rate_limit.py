"""Slowapi 30/min/user_id cap on hot Portal endpoints.

* ``POST /api/portal/availability`` — Emby + TMDB cascade lookup, the
  most expensive read on the platform. Capping it stops a single
  authenticated user from blowing through the TMDB daily quota for
  everyone else.
* ``POST /api/portal/chat/rooms/{room_id}/messages`` — chat send.
  Mute-by-admin handles abusive content; the slowapi cap guards
  against script-driven flooding before a human moderator can react.
"""
from __future__ import annotations

import pytest

from models.portal.profile import UserProfile
from models.user import User
from services.portal.profiles import get_or_create_profile


async def _portal_login(client) -> None:
    """Promote the admin to a portal session via the cascade login."""
    r = await client.post("/api/auth/portal-login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_availability_caps_at_thirty_per_minute(client, admin_user, db_session):
    """A burst of 35 availability checks from one portal session must
    return 429 by the 31st call."""
    await _portal_login(client)

    seen_codes: list[int] = []
    for _ in range(35):
        r = await client.post("/api/portal/availability", json={
            "items": [{"tmdb_id": 1, "media_type": "movie"}],
        })
        seen_codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in seen_codes, f"expected 429 within 35 calls, saw {seen_codes}"
    # Confirm the limit was reached around the configured threshold.
    successes = sum(1 for c in seen_codes if c == 200)
    assert successes <= 30, f"slowapi let through more than 30 successes: {successes}"


@pytest.mark.asyncio
async def test_chat_send_caps_at_thirty_per_minute(client, admin_user, db_session):
    """Same 30/min cap on chat send. Admin profile is created on the
    fly so ``can_chat`` evaluates True."""
    await _portal_login(client)

    # Make sure the admin profile is chat-enabled (auto-created by login).
    profile = await get_or_create_profile(db_session, admin_user)
    profile.role = "admin"
    profile.chat_enabled = True
    profile.can_chat = True
    profile.account_active = True
    db_session.add(profile)
    await db_session.commit()

    # First, list rooms so the default lounge gets created.
    r = await client.get("/api/portal/chat/rooms")
    assert r.status_code == 200
    rooms = r.json()["items"]
    assert rooms, "expected the default lounge to exist"
    room_id = rooms[0]["id"]

    seen_codes: list[int] = []
    for i in range(35):
        r = await client.post(f"/api/portal/chat/rooms/{room_id}/messages", json={
            "content": f"hello {i}",
        })
        seen_codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in seen_codes, f"expected 429 within 35 calls, saw {seen_codes}"
