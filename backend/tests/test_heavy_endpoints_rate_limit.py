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


@pytest.mark.asyncio
async def test_achievements_check_caps_at_six_per_minute(client, admin_user, db_session, portal_login):
    """POST /achievements/check scans achievements + playback each call, so it
    carries a dedicated 6/min cap below the 120/min floor (#382)."""
    await portal_login(client)
    profile = await get_or_create_profile(db_session, admin_user)
    profile.role = "admin"
    profile.account_active = True
    db_session.add(profile)
    await db_session.commit()

    seen_codes: list[int] = []
    for _ in range(8):
        r = await client.post("/api/portal/achievements/check")
        seen_codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in seen_codes, f"expected 429 within 8 calls, saw {seen_codes}"


@pytest.mark.asyncio
async def test_event_party_creation_caps_at_ten_per_minute(client, admin_user, db_session, portal_login):
    """Creating a watch party fans a notification out to every user, so the
    POST is capped at 10/min/account (#408)."""
    await portal_login(client)
    profile = await get_or_create_profile(db_session, admin_user)
    profile.role = "admin"
    profile.account_active = True
    db_session.add(profile)
    await db_session.commit()

    seen_codes: list[int] = []
    for i in range(12):
        r = await client.post("/api/portal/events/parties", json={
            "title": f"party {i}",
            "scheduled_at": "2099-06-01T12:00:00+00:00",
        })
        seen_codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in seen_codes, f"expected 429 within 12 calls, saw {seen_codes}"


@pytest.mark.asyncio
async def test_event_room_creation_caps_at_ten_per_minute(client, admin_user, db_session, portal_login):
    """create_mk_event (POST /events/rooms) shares the 10/min/account cap of
    its sibling party endpoint (#408)."""
    await portal_login(client)
    profile = await get_or_create_profile(db_session, admin_user)
    profile.role = "admin"
    profile.account_active = True
    db_session.add(profile)
    await db_session.commit()

    payload = {
        "title": "room",
        "kind": "private",
        "tmdb_ids": [{"tmdb_id": 1, "media_type": "movie", "title": "M"}],
        "scheduled_at": "2099-06-01T12:00:00+00:00",
        "max_participants": 10,
    }
    seen_codes: list[int] = []
    for _ in range(12):
        r = await client.post("/api/portal/events/rooms", json=payload)
        seen_codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in seen_codes, f"expected 429 within 12 calls, saw {seen_codes}"


@pytest.mark.asyncio
async def test_daily_digest_caps_at_twenty_per_minute(client, admin_user, db_session, portal_login):
    """The new 20/min cap on the daily-digest read endpoint is pinned (#382)."""
    await portal_login(client)
    profile = await get_or_create_profile(db_session, admin_user)
    profile.account_active = True
    db_session.add(profile)
    await db_session.commit()

    seen_codes: list[int] = []
    for _ in range(22):
        r = await client.get("/api/portal/daily-digest")
        seen_codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in seen_codes, f"expected 429 within 22 calls, saw {seen_codes}"
