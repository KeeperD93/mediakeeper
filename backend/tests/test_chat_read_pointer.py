"""Chat read pointer: the panel marks read only what it displayed.

``up_to`` names the newest message the panel showed: the pointer moves up to it,
capped at the latest message, and never back. Without it the pointer snaps to the
latest message, as older clients expect. Synthetic users only.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from core.security import create_access_token
from models.portal.chat import ChatMessage, ChatRoom
from models.portal.profile import UserProfile
from services.portal import chat as chat_svc


async def _lounge(db_session, make_user, count: int) -> tuple[int, int, int, list[int]]:
    """A reader, a poster and ``count`` lounge messages from the poster, as plain ids."""
    reader = await make_user("reader_a", role="viewer")
    poster = await make_user("poster_b", role="viewer")
    room = ChatRoom(type="lounge", name="lounge")
    db_session.add(room)
    await db_session.commit()
    messages = [
        ChatMessage(room_id=room.id, user_id=poster.id, content=f"m{i}", deleted=False)
        for i in range(count)
    ]
    db_session.add_all(messages)
    await db_session.commit()
    return reader.id, poster.id, room.id, [m.id for m in messages]


async def _unread(db_session, user_id: int) -> int:
    db_session.expire_all()  # the route writes through its own session
    return (await chat_svc.get_unread_count(db_session, user_id))["unread"]


@pytest.mark.asyncio
async def test_mark_read_stops_at_the_newest_message_displayed(db_session, make_user):
    reader_id, _, _, ids = await _lounge(db_session, make_user, 3)
    await chat_svc.mark_room_read(db_session, reader_id, up_to=ids[1])
    assert await _unread(db_session, reader_id) == 1


@pytest.mark.asyncio
async def test_mark_read_never_moves_the_pointer_back(db_session, make_user):
    reader_id, _, _, ids = await _lounge(db_session, make_user, 3)
    await chat_svc.mark_room_read(db_session, reader_id, up_to=ids[2])
    await chat_svc.mark_room_read(db_session, reader_id, up_to=ids[0])  # a late request
    assert await _unread(db_session, reader_id) == 0


@pytest.mark.asyncio
async def test_a_late_call_racing_a_newer_one_never_moves_the_pointer_back(db_session, make_user):
    """The late call's session read the profile before the newer call committed."""
    reader_id, _, _, ids = await _lounge(db_session, make_user, 3)
    stale = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == reader_id)
    )).scalar_one()
    assert stale.chat_last_read_message_id is None
    newer_sessions = sessionmaker(bind=db_session.bind, class_=AsyncSession, expire_on_commit=False)
    async with newer_sessions() as newer:
        await chat_svc.mark_room_read(newer, reader_id, up_to=ids[2])

    await chat_svc.mark_room_read(db_session, reader_id, up_to=ids[1])

    assert await _unread(db_session, reader_id) == 0


@pytest.mark.asyncio
async def test_mark_read_caps_up_to_at_the_latest_message(db_session, make_user):
    reader_id, poster_id, room_id, _ = await _lounge(db_session, make_user, 2)
    await chat_svc.mark_room_read(db_session, reader_id, up_to=10**9)
    db_session.add(ChatMessage(room_id=room_id, user_id=poster_id, content="later", deleted=False))
    await db_session.commit()
    assert await _unread(db_session, reader_id) == 1


@pytest.mark.asyncio
async def test_mark_read_route_marks_up_to_the_displayed_message(client, db_session, make_user):
    reader_id, _, _, ids = await _lounge(db_session, make_user, 3)
    await db_session.execute(
        update(UserProfile)
        .where(UserProfile.user_id == reader_id)
        .values(can_chat=True)
        .execution_options(synchronize_session="fetch")
    )
    await db_session.commit()
    client.cookies.set("rq_token", create_access_token({"sub": "reader_a", "scope": "portal"}))

    assert (await client.post("/api/portal/chat/mark-read", json={"up_to": ids[0]})).status_code == 200
    assert await _unread(db_session, reader_id) == 2
    assert (await client.post("/api/portal/chat/mark-read", json={"up_to": 0})).status_code == 422
    assert (await client.post("/api/portal/chat/mark-read", json={"up_to": ids[1], "all": True})).status_code == 422

    assert (await client.post("/api/portal/chat/mark-read", json={})).status_code == 200
    assert await _unread(db_session, reader_id) == 0
