"""Portal chat endpoints (REST + WebSocket)."""
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.csrf_helpers import same_origin, websocket_canonical_origin
from core.database import get_db, AsyncSessionLocal
from core.rate_limit import limiter, portal_user_or_ip_key
from core.security import decode_access_token, is_token_valid_for_revocation_pivot
from models.user import User
from models.portal.profile import UserProfile
from api.auth import PORTAL_COOKIE_NAME
from api.portal.deps import require_permission
from services.portal import chat as chat_svc
from services.portal.profiles import get_or_create_profile

router = APIRouter(prefix="/chat", tags=["portal-chat"])
logger = logging.getLogger("mediakeeper.portal.chat")

# Cadence used by the background task that prunes WebSocket sessions whose
# JWT was revoked while the connection was idle. Exposed as a module-level
# constant so an operator can tune the interval without touching the loop.
WS_REVOCATION_CHECK_INTERVAL_SEC = 300

# Close codes — kept in one place for the test suite.
WS_CLOSE_AUTH_FAILED = 4001
WS_CLOSE_ORIGIN_REJECTED = 4003


class SendMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


# Active WebSocket connections: {room_id: {user_id: (websocket, jwt_iat)}}.
# The iat is stored alongside the socket so the periodic revocation sweep
# can compare it to ``UserProfile.tokens_invalidated_at`` without decoding
# the JWT a second time.
_ws_rooms: dict[int, dict[int, tuple[WebSocket, datetime]]] = {}


def _allowed_origins() -> list[str]:
    """Return the operator-supplied allowlist of origins that may open a
    chat WebSocket. Sources ``FRONTEND_ORIGIN`` (CSV of fully-qualified
    origins). When empty, the helper returns ``[]`` and the caller
    falls back to the auto-derive path (see ``_origin_is_allowed``)."""
    raw = os.getenv("FRONTEND_ORIGIN", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


_AUTO_DERIVE_WARNING_LOGGED = False


def _log_auto_derive_warning_once() -> None:
    """Emit a single warning log when chat falls back to the auto-derive
    path. Repeated handshakes don't spam the logs — the operator only
    needs the hint once per process lifetime."""
    global _AUTO_DERIVE_WARNING_LOGGED
    if _AUTO_DERIVE_WARNING_LOGGED:
        return
    _AUTO_DERIVE_WARNING_LOGGED = True
    logger.warning(
        "[CHAT_WS] FRONTEND_ORIGIN is not set: accepting chat WebSocket "
        "handshakes against the auto-derived canonical origin (Host header "
        "or trusted X-Forwarded-Host). Set FRONTEND_ORIGIN explicitly in "
        "production for stricter posture."
    )


def _origin_is_allowed(origin: str | None, websocket: WebSocket | None = None) -> bool:
    """Decide whether the WebSocket handshake should proceed.

    Two modes:

    1. Operator allowlist — ``FRONTEND_ORIGIN`` env CSV is honoured
       strictly when set.
    2. Auto-derive — when ``FRONTEND_ORIGIN`` is empty, the Origin
       header is compared against the canonical origin derived from
       the WebSocket scope (``Host`` for direct LAN, trusted
       ``X-Forwarded-Host`` for reverse-proxy mode). A WARN line is
       logged once per process so the operator knows to tighten the
       posture for production.
    """
    if not origin:
        return False
    parsed = urlsplit(origin)
    if not parsed.scheme or not parsed.netloc:
        return False
    canonical_request = f"{parsed.scheme}://{parsed.netloc}".lower()

    allow_list = _allowed_origins()
    if allow_list:
        for allowed in allow_list:
            ap = urlsplit(allowed)
            if not ap.scheme or not ap.netloc:
                continue
            if f"{ap.scheme}://{ap.netloc}".lower() == canonical_request:
                return True
        return False

    # Auto-derive fallback — operator did not opt into the allowlist.
    if websocket is None:
        return False
    expected = websocket_canonical_origin(websocket).lower()
    if same_origin(origin, expected):
        _log_auto_derive_warning_once()
        return True
    return False


def _coerce_iat(payload_iat) -> datetime | None:
    if payload_iat is None:
        return None
    try:
        return datetime.fromtimestamp(int(payload_iat), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


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
    user, _ = up
    result = await chat_svc.get_messages(db, room_id, user.id, cursor, limit)
    if isinstance(result, dict) and result.get("error") == "forbidden":
        raise HTTPException(status_code=403, detail="forbidden")
    return result


@router.post("/rooms/{room_id}/messages")
@limiter.limit("30/minute", key_func=portal_user_or_ip_key)
async def send_message(
    room_id: int,
    data: SendMessage,
    request: Request,
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


# Cooldown between two diagnostic WARN lines fired by the WS upgrade
# fallback (HTTP GET on the WS path). One per hour is enough — the hint
# is for the operator, not the attacker.
_WS_UPGRADE_LOG_COOLDOWN_SECONDS = 3600
# Initialised to -inf so the very first occurrence always passes the
# cooldown check, regardless of the value time.monotonic() returns at
# process start (it is monotonic, not Unix epoch).
_last_ws_upgrade_log: float = float("-inf")


def _log_ws_upgrade_missing_once_per_hour() -> None:
    global _last_ws_upgrade_log
    now = time.monotonic()
    if now - _last_ws_upgrade_log < _WS_UPGRADE_LOG_COOLDOWN_SECONDS:
        return
    _last_ws_upgrade_log = now
    logger.warning(
        "[CHAT_WS] received an HTTP GET on the chat WebSocket path. "
        "The reverse proxy is probably not forwarding the Upgrade / "
        "Connection headers. See docs/deployment for the matching "
        "stack (synology-dsm, nginx-proxy-manager, caddy, traefik)."
    )


@router.get("/ws/{room_id}")
async def chat_ws_http_fallback(room_id: int):
    """HTTP GET arriving at the WS path means the reverse proxy did not
    upgrade the connection to a WebSocket. Return 426 with the explicit
    ``Upgrade: websocket`` header and log a one-line operator hint
    (rate-limited 1/h) so the misconfiguration surfaces in container
    logs without flooding them.
    """
    _log_ws_upgrade_missing_once_per_hour()
    return JSONResponse(
        status_code=426,
        content={"detail": "websocket_upgrade_required"},
        headers={"Upgrade": "websocket", "Connection": "Upgrade"},
    )


@router.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: int):
    """WebSocket endpoint for real-time chat."""
    origin = websocket.headers.get("origin")
    if not _origin_is_allowed(origin, websocket=websocket):
        await websocket.close(code=WS_CLOSE_ORIGIN_REJECTED)
        return

    auth = await _authenticate_ws(websocket)
    if not auth:
        await websocket.close(code=WS_CLOSE_AUTH_FAILED)
        return
    user_id, jwt_iat = auth

    # Hand-shake membership gate: refuse the connection if the user is
    # not allowed in this room. Without this, an attacker who knows a
    # private ``room_id`` could open the socket and only fail on send.
    async with AsyncSessionLocal() as db:
        if not await chat_svc.user_can_access_room(db, room_id, user_id):
            await websocket.close(code=WS_CLOSE_AUTH_FAILED)
            return

    await websocket.accept()

    if room_id not in _ws_rooms:
        _ws_rooms[room_id] = {}
    _ws_rooms[room_id][user_id] = (websocket, jwt_iat)

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


async def _authenticate_ws(websocket: WebSocket) -> tuple[int, datetime] | None:
    """Authenticate WebSocket via the Portal-specific cookie.

    Returns ``(user_id, jwt_iat_datetime)`` on success — the ``iat`` is
    surfaced to the caller so the connection can be tracked alongside
    the timestamp used by the periodic revocation sweep.
    """
    token = websocket.cookies.get(PORTAL_COOKIE_NAME)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or payload.get("scope") != "portal":
        return None
    username = payload.get("sub")
    if not username:
        return None
    iat = _coerce_iat(payload.get("iat"))
    if iat is None:
        return None

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
        if not is_token_valid_for_revocation_pivot(payload.get("iat"), profile.tokens_invalidated_at):
            return None
        return user.id, iat


async def _broadcast(room_id: int, message: dict):
    """Broadcast message to all connected WebSocket clients in a room."""
    room = _ws_rooms.get(room_id, {})
    payload = json.dumps({"type": "message", "data": message})
    disconnected = []
    for uid, (ws, _iat) in room.items():
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.append(uid)
    for uid in disconnected:
        room.pop(uid, None)


def _snapshot_connections() -> list[tuple[int, int, WebSocket, datetime]]:
    """Return a flat snapshot ``(room_id, user_id, ws, iat)`` for the sweep."""
    items: list[tuple[int, int, WebSocket, datetime]] = []
    for room_id, members in _ws_rooms.items():
        for user_id, (ws, iat) in members.items():
            items.append((room_id, user_id, ws, iat))
    return items


async def prune_revoked_ws_sessions(db: AsyncSession) -> int:
    """Close every chat WebSocket whose JWT was revoked since handshake.

    Returns the number of sockets closed. Safe to call from a background
    loop — exceptions on individual close calls are swallowed so one
    misbehaving socket never blocks the whole sweep.
    """
    snapshot = _snapshot_connections()
    if not snapshot:
        return 0

    user_ids = list({user_id for _, user_id, _, _ in snapshot})
    rows = (
        await db.execute(
            select(UserProfile.user_id, UserProfile.tokens_invalidated_at).where(
                UserProfile.user_id.in_(user_ids)
            )
        )
    ).all()
    pivots: dict[int, datetime | None] = {uid: ts for uid, ts in rows}

    closed = 0
    for room_id, user_id, ws, iat in snapshot:
        pivot = pivots.get(user_id)
        if pivot is None:
            continue
        if pivot.tzinfo is None:
            pivot = pivot.replace(tzinfo=timezone.utc)
        if iat >= pivot:
            continue
        try:
            await ws.close(code=WS_CLOSE_AUTH_FAILED)
        except Exception:
            pass
        _ws_rooms.get(room_id, {}).pop(user_id, None)
        if room_id in _ws_rooms and not _ws_rooms[room_id]:
            del _ws_rooms[room_id]
        closed += 1
    return closed
