"""Portal chat endpoints (REST + WebSocket)."""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db, AsyncSessionLocal
from core.security import decode_access_token
from models.user import User
from models.portal.profile import UserProfile
from api.auth import PORTAL_COOKIE_NAME
from api.portal.deps import require_permission
from services.portal import chat as chat_svc
from services.portal.profiles import get_or_create_profile

router = APIRouter(prefix="/chat", tags=["portal-chat"])
logger = logging.getLogger("mediakeeper.portal.chat")


class SendMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


# Active WebSocket connections: {room_id: {user_id: websocket}}
_ws_rooms: dict[int, dict[int, WebSocket]] = {}


@router.get("/rooms")
async def list_rooms(
    up: tuple[User, UserProfile] = Depends(require_permission("can_chat")),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await chat_svc.list_rooms(db)}


@router.get("/unread")
async def get_unread(
    up: tuple[User, UserProfile] = Depends(require_permission("can_chat")),
    db: AsyncSession = Depends(get_db),
):
    """Return the unread chat counter for the current user."""
    user, _ = up
    return await chat_svc.get_unread_count(db, user.id)


@router.post("/mark-read")
async def mark_read(
    up: tuple[User, UserProfile] = Depends(require_permission("can_chat")),
    db: AsyncSession = Depends(get_db),
):
    """Snap the user's read pointer to the latest chat message."""
    user, _ = up
    return await chat_svc.mark_room_read(db, user.id)


@router.get("/rooms/{room_id}/messages")
async def get_messages(
    room_id: int,
    cursor: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    up: tuple[User, UserProfile] = Depends(require_permission("can_chat")),
    db: AsyncSession = Depends(get_db),
):
    return await chat_svc.get_messages(db, room_id, cursor, limit)


@router.post("/rooms/{room_id}/messages")
async def send_message(
    room_id: int,
    data: SendMessage,
    up: tuple[User, UserProfile] = Depends(require_permission("can_chat")),
    db: AsyncSession = Depends(get_db),
):
    user, profile = up
    if not profile.chat_enabled:
        raise HTTPException(status_code=403, detail="chat_disabled")
    result = await chat_svc.send_message(db, room_id, user.id, data.content)
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    await _broadcast(room_id, result["message"])
    return result


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    up: tuple[User, UserProfile] = Depends(require_permission("can_chat")),
    db: AsyncSession = Depends(get_db),
):
    user, profile = up
    result = await chat_svc.delete_message(
        db, message_id, user.id, is_admin=(profile.role == "admin")
    )
    if "error" in result:
        code = 404 if result["error"] == "not_found" else 403
        raise HTTPException(status_code=code, detail=result["error"])
    return result


class ReportMessage(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


@router.post("/messages/{message_id}/report")
async def report_message(
    message_id: int,
    data: ReportMessage,
    up: tuple[User, UserProfile] = Depends(require_permission("can_chat")),
    db: AsyncSession = Depends(get_db),
):
    """
    Let any authenticated Portal user flag a chat message.
    The report lands in ``chat_reports`` (handled=false) and a
    notification is pushed to the MediaKeeper admin bell so moderators
    can act on it from the main dashboard.
    """
    user, _ = up
    result = await chat_svc.report_message(db, message_id, user.id, data.reason)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: int):
    """WebSocket endpoint for real-time chat."""
    user_id = await _authenticate_ws(websocket)
    if not user_id:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    if room_id not in _ws_rooms:
        _ws_rooms[room_id] = {}
    _ws_rooms[room_id][user_id] = websocket

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            content = data.get("content", "").strip()
            if not content or len(content) > 2000:
                continue

            async with AsyncSessionLocal() as db:
                result = await chat_svc.send_message(db, room_id, user_id, content)
                if "error" not in result:
                    await _broadcast(room_id, result["message"])
    except WebSocketDisconnect:
        pass
    finally:
        _ws_rooms.get(room_id, {}).pop(user_id, None)
        if room_id in _ws_rooms and not _ws_rooms[room_id]:
            del _ws_rooms[room_id]


async def _authenticate_ws(websocket: WebSocket) -> int | None:
    """Authenticate WebSocket via the Portal-specific cookie."""
    token = websocket.cookies.get(PORTAL_COOKIE_NAME)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or payload.get("scope") != "portal":
        return None
    username = payload.get("sub")
    if not username:
        return None

    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == username, User.is_active == True)  # noqa: E712
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        profile = await get_or_create_profile(db, user)
        if not profile.chat_enabled or not profile.can_chat or not profile.account_active:
            return None
        return user.id


async def _broadcast(room_id: int, message: dict):
    """Broadcast message to all connected WebSocket clients in a room."""
    room = _ws_rooms.get(room_id, {})
    payload = json.dumps({"type": "message", "data": message})
    disconnected = []
    for uid, ws in room.items():
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.append(uid)
    for uid in disconnected:
        room.pop(uid, None)
