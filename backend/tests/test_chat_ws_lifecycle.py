"""Chat WebSocket lifecycle, end to end through the real handler.

Every open socket is watched for its whole life: closed at token expiry, or within
one recheck once the session is revoked or chat access removed, even when the
client never sends a frame. Also covers the handshake refusals, frames that arrive
once the socket is closed, frames the chat cannot read, and the account's socket
slot when the handshake fails. Synthetic users only.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import pytest_asyncio
from sqlalchemy import func, select

import api.portal.chat as chat
from core.security import ALGORITHM, MAX_TOKEN_LENGTH, SECRET_KEY, create_access_token
from models.portal.chat import ChatMessage
from tests._chat_ws_helpers import (
    ChatPeer,
    chat_token,
    leave,
    open_socket,
    seed_lounge,
    update_profile,
    wait_until,
)


@pytest_asyncio.fixture
async def lounge(db_session, make_user, monkeypatch):
    return await seed_lounge(db_session, make_user, monkeypatch)


@pytest.mark.asyncio
async def test_listen_only_socket_is_closed_at_token_expiry(lounge):
    _, room = lounge
    token = chat_token("chatter_a", expires_delta=timedelta(seconds=2))
    peer = ChatPeer(token, room.id)
    task = await open_socket(peer, room.id)
    assert peer.accepted
    await asyncio.wait_for(task, timeout=4)  # the client never sends a frame
    assert peer.close_codes() == [chat.WS_CLOSE_AUTH_FAILED]
    # Not a recheck interval early: the socket lives until the token's exp.
    assert time.time() >= jwt.decode(token, options={"verify_signature": False})["exp"]
    assert room.id not in chat._ws_rooms


@pytest.mark.asyncio
async def test_listen_only_socket_is_closed_after_revocation(lounge, db_session, monkeypatch):
    users, room = lounge
    monkeypatch.setattr(chat, "WS_PERM_RECHECK_INTERVAL_SEC", 0.1)
    peer = ChatPeer(chat_token("chatter_a"), room.id)
    task = await open_socket(peer, room.id)
    await update_profile(db_session, users["chatter_a"].id, tokens_invalidated_at=datetime.now(timezone.utc))
    await asyncio.wait_for(task, timeout=2)
    assert peer.close_codes() == [chat.WS_CLOSE_AUTH_FAILED]


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", ["can_chat", "chat_enabled", "account_active"])
async def test_listen_only_socket_is_closed_when_chat_access_is_removed(
    lounge, db_session, monkeypatch, flag,
):
    users, room = lounge
    monkeypatch.setattr(chat, "WS_PERM_RECHECK_INTERVAL_SEC", 0.1)
    peer = ChatPeer(chat_token("chatter_a"), room.id)
    task = await open_socket(peer, room.id)
    await update_profile(db_session, users["chatter_a"].id, **{flag: False})
    await asyncio.wait_for(task, timeout=2)
    assert peer.close_codes() == [chat.WS_CLOSE_AUTH_FAILED]


@pytest.mark.asyncio
async def test_healthy_socket_stays_open_across_rechecks(lounge, monkeypatch):
    _, room = lounge
    monkeypatch.setattr(chat, "WS_PERM_RECHECK_INTERVAL_SEC", 0.05)
    verdicts: list[bool] = []
    real_check = chat._ws_still_authorized

    async def _recorded(*args):
        verdicts.append(await real_check(*args))
        return verdicts[-1]

    monkeypatch.setattr(chat, "_ws_still_authorized", _recorded)
    peer = ChatPeer(chat_token("chatter_a"), room.id)
    task = await open_socket(peer, room.id)
    await wait_until(lambda: len(verdicts) >= 3)
    assert all(verdicts) and not task.done()
    assert peer.close_codes() == []
    await leave((peer, task))


@pytest.mark.asyncio
async def test_a_socket_opened_just_after_a_revocation_stays_open(lounge, db_session, monkeypatch):
    """The pivot and the new token fall within one second: only the fraction of
    iat tells them apart, at the handshake and at every recheck."""
    users, room = lounge
    monkeypatch.setattr(chat, "WS_PERM_RECHECK_INTERVAL_SEC", 0.05)
    await asyncio.sleep(1 - time.time() % 1 + 0.01)  # just past a whole second
    await update_profile(db_session, users["chatter_a"].id, tokens_invalidated_at=datetime.now(timezone.utc))
    peer = ChatPeer(chat_token("chatter_a"), room.id)
    task = await open_socket(peer, room.id)
    await asyncio.sleep(0.3)  # several rechecks
    assert peer.accepted and not task.done()
    await leave((peer, task))


@pytest.mark.asyncio
async def test_recheck_error_is_logged_and_expiry_still_enforced(lounge, monkeypatch, caplog):
    _, room = lounge
    monkeypatch.setattr(chat, "WS_PERM_RECHECK_INTERVAL_SEC", 0.2)

    async def _db_down(*_args, **_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(chat, "_ws_still_authorized", _db_down)
    peer = ChatPeer(chat_token("chatter_a", expires_delta=timedelta(seconds=2)), room.id)
    with caplog.at_level(logging.WARNING, logger="mediakeeper.portal.chat"):
        task = await open_socket(peer, room.id)
        await asyncio.sleep(0.5)
        assert not task.done(), "a failed recheck must not drop the socket"
        await asyncio.wait_for(task, timeout=4)
    assert peer.close_codes() == [chat.WS_CLOSE_AUTH_FAILED]
    assert any("recheck failed" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_watchdog_does_not_outlive_the_connection(lounge):
    _, room = lounge
    peer = ChatPeer(chat_token("chatter_a"), room.id)
    task = await open_socket(peer, room.id)
    await leave((peer, task))
    await asyncio.sleep(0)
    assert not [t for t in asyncio.all_tasks() if "_ws_watchdog" in repr(t.get_coro())]


@pytest.mark.asyncio
async def test_a_close_while_a_frame_is_processed_ends_the_handler_cleanly(lounge, monkeypatch):
    _, room = lounge
    monkeypatch.setattr(chat, "WS_PERM_RECHECK_INTERVAL_SEC", 0.1)
    release = asyncio.Event()
    real_send = chat.chat_svc.send_message

    async def _slow_send(*args, **kwargs):
        await release.wait()
        return await real_send(*args, **kwargs)

    async def _revoked(*_args, **_kwargs):
        return False

    monkeypatch.setattr(chat.chat_svc, "send_message", _slow_send)
    peer = ChatPeer(chat_token("chatter_a"), room.id)
    task = await open_socket(peer, room.id)
    await peer.say("m1")
    await asyncio.sleep(0.05)  # the handler now waits inside send_message
    monkeypatch.setattr(chat, "_ws_still_authorized", _revoked)
    await asyncio.sleep(0.3)  # the watchdog closes the socket meanwhile
    release.set()
    await asyncio.wait_for(task, timeout=2)  # re-raises if the handler crashed
    assert peer.close_codes() == [chat.WS_CLOSE_AUTH_FAILED]
    assert chat._ws_per_user == {}


@pytest.mark.asyncio
async def test_a_frame_arriving_after_the_close_is_not_posted(lounge, db_session, monkeypatch):
    users, room = lounge
    monkeypatch.setattr(chat, "WS_PERM_RECHECK_INTERVAL_SEC", 0.1)
    peer = ChatPeer(chat_token("chatter_a"), room.id, late_close_reply=True)
    task = await open_socket(peer, room.id)
    await update_profile(db_session, users["chatter_a"].id, tokens_invalidated_at=datetime.now(timezone.utc))
    await wait_until(lambda: peer.close_codes())
    assert peer.close_codes() == [chat.WS_CLOSE_AUTH_FAILED]

    await peer.say("late")  # sent before the client saw the close
    await asyncio.wait_for(task, timeout=2)
    assert (await db_session.execute(select(func.count()).select_from(ChatMessage))).scalar() == 0


@pytest.mark.asyncio
async def test_frames_the_chat_cannot_read_are_skipped(lounge):
    """A binary frame, JSON nested too deep, a number too long to parse, or content
    the database cannot store (a lone surrogate, a NUL): each is ignored and the
    socket keeps working."""
    _, room = lounge
    writer, listener = ChatPeer(chat_token("chatter_a"), room.id), ChatPeer(chat_token("chatter_b"), room.id)
    t_writer, t_listener = await open_socket(writer, room.id), await open_socket(listener, room.id)
    frames = (
        {"bytes": b"\x00\x01"},
        {"text": "[" * 100_000},
        {"text": '{"content": ' + "1" * 5000 + "}"},
        {"text": '{"content": "\\ud800"}'},
        {"text": '{"content": "a\\u0000b"}'},
    )
    for frame in frames:
        await writer.inbox.put({"type": "websocket.receive", **frame})
    await writer.say("still here")
    await wait_until(lambda: listener.contents() == ["still here"])
    await leave((writer, t_writer), (listener, t_listener))


@pytest.mark.asyncio
async def test_a_failed_accept_releases_the_socket_slot(lounge):
    _, room = lounge
    peer = ChatPeer(chat_token("chatter_a"), room.id, fail_accept=True)
    task = await open_socket(peer, room.id)
    with pytest.raises(OSError):
        await asyncio.wait_for(task, timeout=2)
    assert chat._ws_per_user == {}
    assert chat._ws_rooms == {}


@pytest.mark.asyncio
async def test_handshake_refuses_a_token_without_exp(lounge):
    _, room = lounge
    no_exp = jwt.encode(
        {"sub": "chatter_a", "scope": "portal", "iat": int(datetime.now(timezone.utc).timestamp())},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    peer = ChatPeer(no_exp, room.id)
    task = await open_socket(peer, room.id)
    await asyncio.wait_for(task, timeout=2)
    assert not peer.accepted
    assert peer.close_codes() == [chat.WS_CLOSE_AUTH_FAILED]


@pytest.mark.asyncio
async def test_handshake_refuses_an_oversized_token(lounge):
    """Validly signed but past the size cap: only the cap refuses it."""
    _, room = lounge
    oversized = create_access_token({"sub": "chatter_a", "scope": "portal", "pad": "x" * MAX_TOKEN_LENGTH})
    peer = ChatPeer(oversized, room.id)
    task = await open_socket(peer, room.id)
    await asyncio.wait_for(task, timeout=2)
    assert not peer.accepted
    assert peer.close_codes() == [chat.WS_CLOSE_AUTH_FAILED]
