"""Admin actions on one media request: status changes and hard delete.

Re-exported by ``requests.py`` for back-compat.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from constants.notifications import (
    NOTIF_REQUEST_APPROVED,
    NOTIF_REQUEST_AVAILABLE,
    NOTIF_REQUEST_REJECTED,
)
from constants.requests import REQUEST_APPROVED, REQUEST_AVAILABLE, REQUEST_REJECTED
from models.portal.request import MediaRequest
from services.portal.requests_blacklist import maybe_blacklist_media

logger = logging.getLogger("mediakeeper.portal.requests")


async def delete_request(db: AsyncSession, request_id: int) -> dict:
    """Admin: hard-delete a request entirely (no trace).

    Different from ``update_request_status(..., "rejected")`` — that one
    keeps the row and logs a reject reason. Hard-delete wipes the row so
    the original requester can re-submit freely and the item disappears
    from every admin queue. Irreversible.
    """
    req = await db.get(MediaRequest, request_id)
    if not req:
        return {"error": "not_found"}
    await db.delete(req)
    await db.commit()
    return {"success": True}


async def update_request_status(
    db: AsyncSession,
    request_id: int,
    new_status: str,
    admin_id: int,
    reason: str | None = None,
    *,
    force: bool = False,
) -> dict:
    """Admin: approve/reject/mark-available a request.
    Side-effects:
      - `approved` → bell notification to the original requester; from
        `available` it silently undoes a wrong availability instead
      - `available` → bell notification (media landed in Emby); refused with
        ``not_in_library`` / ``library_check_failed`` while Emby does not
        verifiably hold the content, unless ``force`` (admin confirmed)
      - `rejected` → bell notification carrying the reason; once the media's
        live (non-archived) rejections reach BLACKLIST_REJECT_THRESHOLD, it's
        auto-added to the blacklist (hidden from every user-facing list until
        an admin unblocks it).
    Resending the status a request already has (from a stale queue, after
    the automatic flip for instance) changes and notifies nothing.
    """
    req = await db.get(MediaRequest, request_id)
    if not req:
        return {"error": "not_found"}
    if new_status == req.status:
        return {"success": True, "user_id": req.user_id}
    undo_available = req.status == REQUEST_AVAILABLE and new_status == REQUEST_APPROVED
    if new_status == REQUEST_AVAILABLE:
        if not force:
            error = await _library_check_error(db, req)
            if error:
                return {"error": error}
        # Starts the auto-archive delay.
        req.available_at = datetime.now(timezone.utc)
    if undo_available:
        # The automatic flip redoes it once Emby really holds the content.
        req.available_at = None
    # A stale queue line can act on a request archived meanwhile: bring it
    # back, it must not stay hidden while blocking new requests for the title.
    req.archived_at = None
    req.status = new_status
    if new_status == REQUEST_APPROVED and not undo_available:
        req.approved_by = admin_id
    if new_status == REQUEST_REJECTED and reason:
        req.reject_reason = reason
    db.add(req)
    await db.flush()

    from services.portal import notifications as notif_svc
    payload = {
        "tmdb_id": req.tmdb_id,
        "media_type": req.media_type,
        "title": req.title,
        "poster_url": req.poster_url,
        "request_id": req.id,
    }
    # Skip the user-bound bell when the requester has been GDPR-purged
    # (FK ``SET NULL`` since migration 041): ``mk_notifications.user_id``
    # is NOT NULL, so an insert with ``None`` would crash. The admin
    # action itself still succeeds.
    if new_status == REQUEST_APPROVED and not undo_available and req.user_id is not None:
        await notif_svc.create(db, req.user_id, NOTIF_REQUEST_APPROVED, payload)
    elif new_status == REQUEST_AVAILABLE and req.user_id is not None:
        await notif_svc.create(db, req.user_id, NOTIF_REQUEST_AVAILABLE, payload)
    elif new_status == REQUEST_REJECTED:
        if req.user_id is not None:
            await notif_svc.create(
                db, req.user_id, NOTIF_REQUEST_REJECTED, {**payload, "reason": reason or None},
            )
        await maybe_blacklist_media(db, req, admin_id)

    await db.commit()
    # Surface the requester so the API layer can trigger the achievement
    # runner for the original user (e.g. ambassador on `approved`).
    return {"success": True, "user_id": req.user_id}


async def _library_check_error(db: AsyncSession, req: MediaRequest) -> str | None:
    """Why ``req`` cannot be marked available yet, None when Emby holds it."""
    from services.portal.requests_fulfill import is_request_in_library
    try:
        return None if await is_request_in_library(db, req) else "not_in_library"
    except Exception:
        # Only an unexpected failure lands here: Emby or TMDB outages read as a
        # title Emby does not hold. Either way the admin decides.
        logger.warning("[REQUEST] library check failed for request_id=%s", req.id, exc_info=True)
        return "library_check_failed"
