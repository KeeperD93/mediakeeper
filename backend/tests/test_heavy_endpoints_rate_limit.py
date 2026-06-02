"""Slowapi cap on hot Portal endpoints.

* ``POST /api/portal/chat/rooms/{room_id}/messages`` — chat send,
  30/min/user_id. Mute-by-admin handles abusive content; the slowapi
  cap guards against script-driven flooding before a human moderator
  can react.

The availability endpoint used to be pinned here at 30/min too, but
the Home page legitimately bursts that limit with 13 carousels. Its
dedicated rate-limit contract now lives in
``test_availability_rate_limit.py`` at the higher 120/min ceiling.
"""
from __future__ import annotations

import pytest

from models.portal.profile import UserProfile
from models.user import User
from services.portal.profiles import get_or_create_profile


@pytest.mark.asyncio
async def test_chat_send_caps_at_thirty_per_minute(client, admin_user, db_session, portal_login):
    """Same 30/min cap on chat send. Admin profile is created on the
    fly so ``can_chat`` evaluates True."""
    await portal_login(client)

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
