"""Shared harness for the chat WebSocket tests: an in-process ASGI client that
drives the real handler, plus the helpers around it.

Loaded by ``test_chat_ws_lifecycle.py`` and ``test_chat_ws_fanout.py``.
"""
from __future__ import annotations

import asyncio
import json
import time

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette.websockets import WebSocket

import api.portal.chat as chat
from core.security import create_access_token
from models.portal.chat import ChatRoom
from models.portal.profile import UserProfile


class ChatPeer:
    """In-process ASGI WebSocket client. Like uvicorn, a server-side close after
    the handshake ends the pending receive with a disconnect, unless
    ``late_close_reply`` holds it back: frames already in flight arrive first.
    ``handshake_delay`` stretches the accept as a slow network would,
    ``fail_accept`` drops the client mid-handshake and ``stall_sends`` makes it
    stop reading."""

    def __init__(self, token: str, room_id: int, *, handshake_delay: float = 0.0,
                 late_close_reply: bool = False, fail_accept: bool = False,
                 stall_sends: bool = False):
        self.handshake_delay, self.late_close_reply = handshake_delay, late_close_reply
        self.fail_accept, self.stall_sends = fail_accept, stall_sends
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.sent: list[dict] = []
        self.scope = {
            "type": "websocket",
            "path": f"/api/portal/chat/ws/{room_id}",
            "scheme": "ws",
            "headers": [
                (b"host", b"test"),
                (b"origin", b"http://test"),
                (b"cookie", f"rq_token={token}".encode()),
            ],
            "client": ("127.0.0.1", 5555),
            "server": ("test", 80),
            "query_string": b"",
            "subprotocols": [],
        }

    async def receive(self):
        return await self.inbox.get()

    async def send(self, message):
        if message["type"] == "websocket.accept":
            if self.fail_accept:
                raise OSError("the client left mid-handshake")
            await asyncio.sleep(self.handshake_delay)
        elif message["type"] == "websocket.send" and self.stall_sends:
            await asyncio.Event().wait()
        self.sent.append(message)
        if message["type"] == "websocket.close" and self.accepted and not self.late_close_reply:
            await self.inbox.put({"type": "websocket.disconnect", "code": message.get("code", 1000)})

    @property
    def accepted(self) -> bool:
        return any(m["type"] == "websocket.accept" for m in self.sent)

    def close_codes(self) -> list[int]:
        return [m.get("code") for m in self.sent if m["type"] == "websocket.close"]

    def contents(self) -> list[str]:
        return [
            json.loads(m["text"])["data"]["content"]
            for m in self.sent
            if m["type"] == "websocket.send"
        ]

    async def say(self, content: str) -> None:
        await self.inbox.put({"type": "websocket.receive", "text": json.dumps({"content": content})})


async def wait_until(condition, timeout: float = 2.0) -> None:
    """Poll ``condition`` until it holds; fail once ``timeout`` seconds are up."""
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        await asyncio.sleep(0.02)


async def open_socket(peer: ChatPeer, room_id: int) -> asyncio.Task:
    """Start the real handler for ``peer`` and wait for its accept or refusal."""
    await peer.inbox.put({"type": "websocket.connect"})
    task = asyncio.create_task(
        chat.websocket_chat(WebSocket(peer.scope, peer.receive, peer.send), room_id)
    )
    await wait_until(lambda: peer.sent or task.done())
    return task


async def leave(*pairs: tuple[ChatPeer, asyncio.Task]) -> None:
    """Disconnect the peers still open and wait for their handlers, which must not raise."""
    for peer, task in pairs:
        if not task.done():
            await peer.inbox.put({"type": "websocket.disconnect", "code": 1000})
    await asyncio.wait_for(asyncio.gather(*(task for _, task in pairs)), timeout=5)


def chat_token(username: str, **kwargs) -> str:
    return create_access_token({"sub": username, "scope": "portal"}, **kwargs)


async def update_profile(db_session, user_id: int, **values) -> None:
    await db_session.execute(
        update(UserProfile)
        .where(UserProfile.user_id == user_id)
        .values(**values)
        .execution_options(synchronize_session="fetch")
    )
    await db_session.commit()


async def seed_lounge(db_session, make_user, monkeypatch):
    """Two chatters and the lounge. The handler opens its own DB sessions: bind
    them to the test engine instead of the app's."""
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://test")
    monkeypatch.setattr(
        chat,
        "AsyncSessionLocal",
        sessionmaker(bind=db_session.bind, class_=AsyncSession, expire_on_commit=False),
    )
    users = {name: await make_user(name, role="viewer") for name in ("chatter_a", "chatter_b")}
    for user in users.values():
        await update_profile(db_session, user.id, can_chat=True, chat_enabled=True)
    room = ChatRoom(type="lounge", name="lounge")
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)
    return users, room
