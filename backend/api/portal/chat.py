"""Portal chat endpoints (REST + WebSocket)."""
import asyncio
import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.csrf_helpers import same_origin, websocket_canonical_origin
from core.database import get_db, AsyncSessionLocal
from core.rate_limit import limiter, portal_user_or_ip_key
from core.security import decode_access_token, is_token_valid_for_revocation_pivot
from models.user import User
from models.portal.profile import UserProfile
from api.auth import PORTAL_COOKIE_NAME
from api.portal._chat_schemas import MarkRead, ReportMessage, SendMessage, is_storable
from api.portal.deps import get_request_lang, require_permission
from services.portal import chat as chat_svc
from services.portal.achievements import safe_check_all_achievements_in_new_session
from services.portal.profiles import get_or_create_profile
from services.portal.admin_users_constants import ROLE_ADMIN

router = APIRouter(prefix="/chat", tags=["portal-chat"])
logger = logging.getLogger("mediakeeper.portal.chat")

# Close codes — kept in one place for the test suite.
WS_CLOSE_AUTH_FAILED = 4001
WS_CLOSE_ORIGIN_REJECTED = 4003
WS_CLOSE_TOO_MANY_SOCKETS = 4029
# Dropped by a broadcast it could not take in time; the client reconnects and catches up.
WS_CLOSE_STALLED = 4008

# WebSocket message throttle, per connection: the socket path bypasses the HTTP
# limiter on POST /messages, so each socket gets that 30/min ceiling here.
WS_MSG_LIMIT = 30
WS_MSG_WINDOW_SEC = 60
# How often each open socket re-validates the session and chat permission,
# whether or not the client ever sends a frame (the portal client only listens).
WS_PERM_RECHECK_INTERVAL_SEC = 30
# Sockets one account may hold at once (tabs and devices): each is rechecked
# every 30 s and receives every broadcast.
WS_MAX_SOCKETS_PER_USER = 10
# A peer that cannot take a message within this delay has stopped reading: it is
# dropped instead of holding up the room.
WS_SEND_TIMEOUT_SEC = 5


# Active WebSocket connections: {room_id: {websocket: user_id}}. One entry per
# connection, so a second tab or device never evicts the first.
_ws_rooms: dict[int, dict[WebSocket, int]] = {}
# Open sockets per account, counted from the handshake so that concurrent
# handshakes cannot slip past WS_MAX_SOCKETS_PER_USER.
_ws_per_user: dict[int, int] = {}


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


def _coerce_epoch(value) -> datetime | None:
    if value is None:
        return None
    try:
        # float: iat carries a fraction, and a pivot can fall inside the same second.
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _over_rate_limit(times: deque, now: float) -> bool:
    """Sliding-window throttle for the chat WebSocket: returns ``True`` (drop
    the message) once ``WS_MSG_LIMIT`` messages were sent within the last
    ``WS_MSG_WINDOW_SEC``. Mutates ``times`` — evicts expired stamps and
    records ``now`` when the message is allowed through."""
    while times and now - times[0] > WS_MSG_WINDOW_SEC:
        times.popleft()
    if len(times) >= WS_MSG_LIMIT:
        return True
    times.append(now)
    return False


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
    data: MarkRead | None = None,
    up: tuple[User, UserProfile] = Depends(require_permission("can_chat")),
    db: AsyncSession = Depends(get_db),
):
    """Move the user's read pointer up to the newest message the panel displayed,
    or to the latest chat message when the client names none."""
    user, _ = up
    return await chat_svc.mark_room_read(db, user.id, up_to=data.up_to if data else None)


@router.get("/rooms/{room_id}/messages")
async def get_messages(
    room_id: int,
    cursor: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    up: tuple[User, UserProfile] = Depends(require_permission("can_chat")),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_lang),
):
    user, _ = up
    result = await chat_svc.get_messages(db, room_id, user.id, cursor, limit, lang=lang)
    if isinstance(result, dict) and result.get("error") == "forbidden":
        raise HTTPException(status_code=403, detail="forbidden")
    return result


@router.post("/rooms/{room_id}/messages")
@limiter.limit("30/minute", key_func=portal_user_or_ip_key)
async def send_message(
    room_id: int,
    data: SendMessage,
    request: Request,
    background_tasks: BackgroundTasks,
    up: tuple[User, UserProfile] = Depends(require_permission("can_chat")),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_lang),
):
    user, profile = up
    if not profile.chat_enabled:
        raise HTTPException(status_code=403, detail="chat_disabled")
    result = await chat_svc.send_message(db, room_id, user.id, data.content, lang=lang)
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    # End the read transaction send_message leaves open: a slow peer must never
    # pin a pooled DB connection during the fan-out.
    await db.commit()
    await _broadcast(room_id, result["message"])
    background_tasks.add_task(
        safe_check_all_achievements_in_new_session,
        user.id,
        user.username,
        "chat_message",
    )
    return result


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    up: tuple[User, UserProfile] = Depends(require_permission("can_chat")),
    db: AsyncSession = Depends(get_db),
):
    user, profile = up
    result = await chat_svc.delete_message(
        db, message_id, user.id, is_admin=(profile.role == ROLE_ADMIN)
    )
    if "error" in result:
        code = 404 if result["error"] == "not_found" else 403
        raise HTTPException(status_code=code, detail=result["error"])
    return result


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
    user_id, jwt_iat, jwt_exp = auth

    # Hand-shake membership gate: refuse the connection if the user is
    # not allowed in this room. Without this, an attacker who knows a
    # private ``room_id`` could open the socket and only fail on send.
    async with AsyncSessionLocal() as db:
        if not await chat_svc.user_can_access_room(db, room_id, user_id):
            await websocket.close(code=WS_CLOSE_AUTH_FAILED)
            return

    if _ws_per_user.get(user_id, 0) >= WS_MAX_SOCKETS_PER_USER:
        await websocket.close(code=WS_CLOSE_TOO_MANY_SOCKETS)
        return
    _ws_per_user[user_id] = _ws_per_user.get(user_id, 0) + 1

    watchdog = None
    msg_times: deque = deque()
    try:
        await websocket.accept()
        _ws_rooms.setdefault(room_id, {})[websocket] = user_id
        watchdog = asyncio.create_task(_ws_watchdog(websocket, room_id, user_id, jwt_iat, jwt_exp))
        while True:
            message = await websocket.receive()
            # The watchdog may have closed the socket from its own task: a frame
            # read after that is not posted.
            if (message["type"] == "websocket.disconnect"
                    or websocket.application_state != WebSocketState.CONNECTED):
                break
            raw = message.get("text")
            if raw is None:
                continue  # binary frame: the chat speaks text only
            try:
                data = json.loads(raw)
            except (ValueError, RecursionError):  # malformed, nested too deep or a huge number
                continue
            if not isinstance(data, dict):
                continue

            content = data.get("content")
            if not isinstance(content, str):
                continue
            content = content.strip()
            if not content or len(content) > 2000 or not is_storable(content):
                continue

            # Anti-spam: the socket bypasses the HTTP limiter, so throttle here.
            if _over_rate_limit(msg_times, time.monotonic()):
                continue

            async with AsyncSessionLocal() as db:
                result = await chat_svc.send_message(db, room_id, user_id, content)
            # Session closed first: a slow peer must never pin a pooled DB connection.
            if "error" not in result:
                await _broadcast(room_id, result["message"])
    except WebSocketDisconnect:
        pass
    finally:
        _ws_rooms.get(room_id, {}).pop(websocket, None)
        if room_id in _ws_rooms and not _ws_rooms[room_id]:
            del _ws_rooms[room_id]
        if _ws_per_user[user_id] > 1:
            _ws_per_user[user_id] -= 1
        else:
            del _ws_per_user[user_id]
        if watchdog:
            # Let a recheck caught mid-query unwind before the handler returns.
            watchdog.cancel()
            await asyncio.gather(watchdog, return_exceptions=True)


async def _authenticate_ws(websocket: WebSocket) -> tuple[int, datetime, datetime] | None:
    """Authenticate WebSocket via the Portal-specific cookie.

    Returns ``(user_id, jwt_iat, jwt_exp)`` on success: the watchdog needs both
    timestamps to enforce revocation and expiry for the life of the connection.
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
    iat = _coerce_epoch(payload.get("iat"))
    exp = _coerce_epoch(payload.get("exp"))
    if iat is None or exp is None:
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
        return user.id, iat, exp


async def _ws_still_authorized(db: AsyncSession, user_id: int, jwt_iat: datetime) -> bool:
    """Re-check, mid-session, that the user may still chat: active account,
    chat permission not revoked, and JWT not invalidated since the handshake.
    Lets a permission change take effect within one watchdog tick, without a
    global token bump that would log the user out everywhere."""
    row = (await db.execute(
        select(
            UserProfile.chat_enabled,
            UserProfile.can_chat,
            UserProfile.account_active,
            UserProfile.tokens_invalidated_at,
        ).where(UserProfile.user_id == user_id)
    )).first()
    if not row:
        return False
    if not row.chat_enabled or not row.can_chat or not row.account_active:
        return False
    return is_token_valid_for_revocation_pivot(jwt_iat.timestamp(), row.tokens_invalidated_at)


async def _ws_watchdog(
    websocket: WebSocket, room_id: int, user_id: int, jwt_iat: datetime, jwt_exp: datetime,
) -> None:
    """Close the socket at token expiry, once a periodic recheck finds the session
    revoked or chat access removed, or once a broadcast dropped it for not reading,
    even if the client never sends a frame."""
    code = WS_CLOSE_AUTH_FAILED
    while (remaining := (jwt_exp - datetime.now(timezone.utc)).total_seconds()) > 0:
        await asyncio.sleep(min(remaining, WS_PERM_RECHECK_INTERVAL_SEC))
        if datetime.now(timezone.utc) >= jwt_exp:
            break
        if websocket not in _ws_rooms.get(room_id, {}):
            # Left behind by _send_or_drop: closing it makes the client reconnect and catch up.
            code = WS_CLOSE_STALLED
            break
        try:
            async with AsyncSessionLocal() as db:
                if not await _ws_still_authorized(db, user_id, jwt_iat):
                    break
        except Exception as exc:
            # A DB hiccup must not drop every socket; expiry stays enforced.
            logger.warning("[CHAT_WS] recheck failed for user_id=%s: %s", user_id, exc)
    try:
        await websocket.close(code=code)
    except Exception:  # noqa: S110 -- the peer may already be gone
        pass


async def _broadcast(room_id: int, message: dict):
    """Broadcast message to all connected WebSocket clients in a room."""
    room = _ws_rooms.get(room_id, {})
    payload = json.dumps({"type": "message", "data": message})
    # All peers at once, each within a deadline: a client that stops reading
    # must not hold up the room. Works on a snapshot, as peers come and go.
    await asyncio.gather(*(_send_or_drop(room, ws, payload) for ws in list(room)))


async def _send_or_drop(room: dict[WebSocket, int], ws: WebSocket, payload: str) -> None:
    try:
        await asyncio.wait_for(ws.send_text(payload), WS_SEND_TIMEOUT_SEC)
    except Exception as exc:
        # Peer gone or stalled: drop it from the room. A gone peer's handler cleans
        # up; the watchdog closes a stalled one at its next tick.
        if (user_id := room.pop(ws, None)) is not None:
            logger.info("[CHAT_WS] user_id=%s dropped from the room: %r", user_id, exc)
