"""Membership gate on chat rooms.

Today the lounge is the only seeded room and every chat-enabled user
gets in. The schema, however, supports request-linked and event-linked
rooms — once those land, ``user_can_access_room`` becomes the single
chokepoint. These tests pin the contract:

* ``lounge`` (default) — accessible to any chat-enabled user.
* unknown room types — refused. Future room types must opt into the
  allow-list explicitly so a forgotten branch cannot leak access.
* unknown ``room_id`` — refused (no information leak about existence).
"""
from __future__ import annotations

import pytest

from models.portal.chat import ChatRoom
from services.portal import chat as chat_svc
from services.portal.profiles import get_or_create_profile


async def _portal_login_admin(client) -> None:
    r = await client.post("/api/auth/portal-login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_user_can_access_room_returns_true_for_lounge(db_session):
    """The seeded lounge stays accessible to keep the FAB chat working."""
    room = ChatRoom(type="lounge", name="lounge")
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)

    assert await chat_svc.user_can_access_room(db_session, room.id, user_id=42) is True


@pytest.mark.asyncio
async def test_user_can_access_room_refuses_unknown_type(db_session):
    """Any other room type defaults to refused — fail-closed posture."""
    room = ChatRoom(type="event", name="party-room-7")
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)

    assert await chat_svc.user_can_access_room(db_session, room.id, user_id=42) is False


@pytest.mark.asyncio
async def test_user_can_access_room_refuses_unknown_id(db_session):
    """A non-existent room_id returns False, not an exception. Prevents
    leaking room existence through error shape."""
    assert await chat_svc.user_can_access_room(db_session, 99_999, user_id=42) is False


@pytest.mark.asyncio
async def test_send_message_refuses_when_room_is_private(client, admin_user, db_session):
    """``POST /chat/rooms/{room_id}/messages`` must return an error when
    the user is not allowed in the room — even if they are chat-enabled."""
    await _portal_login_admin(client)

    profile = await get_or_create_profile(db_session, admin_user)
    profile.role = "admin"
    profile.chat_enabled = True
    profile.can_chat = True
    profile.account_active = True
    db_session.add(profile)

    private_room = ChatRoom(type="event", name="party-room-7")
    db_session.add(private_room)
    await db_session.commit()
    await db_session.refresh(private_room)

    r = await client.post(
        f"/api/portal/chat/rooms/{private_room.id}/messages",
        json={"content": "trying to crash the party"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_messages_refuses_when_room_is_private(client, admin_user, db_session):
    """Same gate on the read path — listing a private room's history
    from a non-member returns 403, not the messages."""
    await _portal_login_admin(client)

    profile = await get_or_create_profile(db_session, admin_user)
    profile.role = "admin"
    profile.chat_enabled = True
    profile.can_chat = True
    profile.account_active = True
    db_session.add(profile)

    private_room = ChatRoom(type="event", name="party-room-8")
    db_session.add(private_room)
    await db_session.commit()
    await db_session.refresh(private_room)

    r = await client.get(f"/api/portal/chat/rooms/{private_room.id}/messages")
    assert r.status_code == 403
