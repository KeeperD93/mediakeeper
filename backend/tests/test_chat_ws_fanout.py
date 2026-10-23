"""Chat WebSocket fan-out, end to end through the real handler.

One registry entry per connection (two tabs of one user), the per-account socket
cap, the per-socket message throttle, and the broadcast: concurrent, a stalled peer
dropped and then closed so its client reconnects, and no DB connection held while
it runs. Synthetic users only.
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy import func, select

import api.portal.chat as chat
from models.portal.chat import ChatMessage
from tests._chat_ws_helpers import ChatPeer, chat_token, leave, open_socket, seed_lounge, wait_until


@pytest_asyncio.fixture
async def lounge(db_session, make_user, monkeypatch):
    return await seed_lounge(db_session, make_user, monkeypatch)


@pytest.mark.asyncio
async def test_two_tabs_of_one_user_both_receive_and_survive_each_other(lounge):
    _, room = lounge
    tab1, tab2 = ChatPeer(chat_token("chatter_a"), room.id), ChatPeer(chat_token("chatter_a"), room.id)
    other = ChatPeer(chat_token("chatter_b"), room.id)
    t1, t2, t_other = await open_socket(tab1, room.id), await open_socket(tab2, room.id), await open_socket(other, room.id)
    await other.say("m1")
    await wait_until(lambda: tab1.contents() == ["m1"] and tab2.contents() == ["m1"])
    await leave((tab1, t1))
    await other.say("m2")
    await wait_until(lambda: tab2.contents() == ["m1", "m2"])
    await leave((tab2, t2), (other, t_other))


@pytest.mark.asyncio
async def test_messages_over_the_socket_quota_are_dropped(lounge, db_session, monkeypatch):
    _, room = lounge
    monkeypatch.setattr(chat, "WS_MSG_LIMIT", 2)
    writer, listener = ChatPeer(chat_token("chatter_a"), room.id), ChatPeer(chat_token("chatter_b"), room.id)
    t_writer, t_listener = await open_socket(writer, room.id), await open_socket(listener, room.id)
    for content in ("m1", "m2", "m3"):
        await writer.say(content)
    await wait_until(lambda: listener.contents() == ["m1", "m2"])
    await asyncio.sleep(0.2)  # room for a third message that must never come
    assert listener.contents() == ["m1", "m2"]
    assert (await db_session.execute(select(func.count()).select_from(ChatMessage))).scalar() == 2
    await leave((writer, t_writer), (listener, t_listener))


class _Recorder:
    """Stand-in peer for _broadcast: records what it got, optionally slowly or never."""

    def __init__(self, name: str, received: list[str], delay: float = 0.0, stalled: bool = False):
        self.name, self.received, self.delay, self.stalled = name, received, delay, stalled

    async def send_text(self, payload):
        if self.stalled:
            await asyncio.Event().wait()  # a client that stopped reading
        await asyncio.sleep(self.delay)
        self.received.append(self.name)


@pytest.mark.asyncio
async def test_broadcast_tolerates_a_peer_joining_mid_send():
    received: list[str] = []
    chat._ws_rooms[1] = {_Recorder("slow", received, delay=0.05): 1, _Recorder("fast", received): 2}

    async def _late_join():
        await asyncio.sleep(0.01)
        chat._ws_rooms[1][_Recorder("late", received)] = 3

    await asyncio.gather(chat._broadcast(1, {"id": 1}), _late_join())
    assert sorted(received) == ["fast", "slow"]


@pytest.mark.asyncio
async def test_a_stalled_peer_is_dropped_without_holding_up_the_room(monkeypatch):
    monkeypatch.setattr(chat, "WS_SEND_TIMEOUT_SEC", 0.5)
    received: list[str] = []
    stalled, healthy = _Recorder("stalled", received, stalled=True), _Recorder("healthy", received)
    chat._ws_rooms[1] = {stalled: 1, healthy: 2}
    fan_out = asyncio.create_task(chat._broadcast(1, {"id": 1}))
    try:
        await asyncio.sleep(0.1)
        assert received == ["healthy"]  # served at once, not after the stalled peer's deadline
        await asyncio.wait_for(fan_out, timeout=2)
        assert list(chat._ws_rooms[1]) == [healthy]
    finally:
        fan_out.cancel()
        await asyncio.gather(fan_out, return_exceptions=True)


@pytest.mark.asyncio
async def test_a_peer_dropped_for_not_reading_is_closed_so_its_client_reconnects(lounge, monkeypatch):
    """Dropped from the room, the socket would otherwise stay open and silent until
    its token expires: the watchdog closes it at its next tick."""
    _, room = lounge
    monkeypatch.setattr(chat, "WS_SEND_TIMEOUT_SEC", 0.1)
    monkeypatch.setattr(chat, "WS_PERM_RECHECK_INTERVAL_SEC", 0.1)
    stalled = ChatPeer(chat_token("chatter_a"), room.id, stall_sends=True)
    writer = ChatPeer(chat_token("chatter_b"), room.id)
    t_stalled, t_writer = await open_socket(stalled, room.id), await open_socket(writer, room.id)

    await writer.say("m1")  # the stalled peer cannot take it
    await asyncio.wait_for(t_stalled, timeout=2)

    assert stalled.close_codes() == [chat.WS_CLOSE_STALLED]
    assert writer.contents() == ["m1"]
    await leave((writer, t_writer))
    assert chat._ws_per_user == {}


@pytest.mark.asyncio
async def test_the_db_connection_is_released_before_the_socket_fan_out(lounge, monkeypatch):
    _, room = lounge
    sessions, in_transaction = [], []
    real_send, real_broadcast = chat.chat_svc.send_message, chat._broadcast

    async def _spy_send(db, *args, **kwargs):
        sessions.append(db)
        return await real_send(db, *args, **kwargs)

    async def _spy_broadcast(room_id, message):
        in_transaction.append(sessions[-1].in_transaction())
        await real_broadcast(room_id, message)

    monkeypatch.setattr(chat.chat_svc, "send_message", _spy_send)
    monkeypatch.setattr(chat, "_broadcast", _spy_broadcast)
    writer = ChatPeer(chat_token("chatter_a"), room.id)
    task = await open_socket(writer, room.id)
    await writer.say("m1")
    await wait_until(lambda: in_transaction)
    assert in_transaction == [False]
    await leave((writer, task))


@pytest.mark.asyncio
async def test_the_db_connection_is_released_before_the_post_fan_out(lounge, client, monkeypatch):
    _, room = lounge
    sessions, in_transaction = [], []
    real_send, real_broadcast = chat.chat_svc.send_message, chat._broadcast

    async def _spy_send(db, *args, **kwargs):
        sessions.append(db)
        return await real_send(db, *args, **kwargs)

    async def _spy_broadcast(room_id, message):
        in_transaction.append(sessions[-1].in_transaction())
        await real_broadcast(room_id, message)

    async def _no_achievements(*_args):
        return None

    monkeypatch.setattr(chat.chat_svc, "send_message", _spy_send)
    monkeypatch.setattr(chat, "_broadcast", _spy_broadcast)
    monkeypatch.setattr(chat, "safe_check_all_achievements_in_new_session", _no_achievements)
    client.cookies.set("rq_token", chat_token("chatter_a"))
    resp = await client.post(f"/api/portal/chat/rooms/{room.id}/messages", json={"content": "m1"})
    assert resp.status_code == 200
    assert in_transaction == [False]


@pytest.mark.asyncio
async def test_an_account_cannot_hold_more_sockets_than_the_cap(lounge, monkeypatch):
    _, room = lounge
    monkeypatch.setattr(chat, "WS_MAX_SOCKETS_PER_USER", 3)
    # Concurrent handshakes, each accept slow enough to overlap the others.
    tabs = [ChatPeer(chat_token("chatter_a"), room.id, handshake_delay=0.2) for _ in range(4)]
    tasks = await asyncio.gather(*(open_socket(tab, room.id) for tab in tabs))
    opened = [(tab, task) for tab, task in zip(tabs, tasks) if tab.accepted]
    refused = [(tab, task) for tab, task in zip(tabs, tasks) if not tab.accepted]
    assert len(opened) == 3
    refused_tab, refused_task = refused[0]
    await asyncio.wait_for(refused_task, timeout=2)
    assert refused_tab.close_codes() == [chat.WS_CLOSE_TOO_MANY_SOCKETS]

    other = ChatPeer(chat_token("chatter_b"), room.id)  # another account is not affected
    t_other = await open_socket(other, room.id)
    assert other.accepted

    await leave(opened[0])  # a tab closing frees its slot
    again = ChatPeer(chat_token("chatter_a"), room.id)
    t_again = await open_socket(again, room.id)
    assert again.accepted

    await leave(*opened[1:], (other, t_other), (again, t_again))
    assert chat._ws_per_user == {}
