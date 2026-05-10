"""Auto-fulfillment of pending media requests when Emby reports a match.

Plugged into the ``added_media`` notification pipeline: every time the
scheduler sees a fresh Emby item, we try to flip any matching pending
request to ``available`` and drop a notification on the requester's
bell. The flip is idempotent (a re-scan never re-notifies) and atomic
(the status update + bell insertion ride a single SAVEPOINT so a
transient failure cannot leave the request in a half-fulfilled state).
"""
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.request import MediaRequest
from services.portal import notifications as notif_svc

logger = logging.getLogger("mediakeeper.notifications.requests")

REQUEST_AVAILABLE_STATUS = "available"
REQUEST_FULFILLED_NOTIF_TYPE = "request_available"
ACTIONABLE_STATUSES = ("pending", "approved")


def _emby_to_tmdb_match(item: dict) -> tuple[int, str] | None:
    """Return ``(tmdb_id, media_type)`` for the matching MediaRequest row.

    Episodes resolve to the parent series' TMDB id (TV requests are
    series-wide). Movies use their own TMDB id. Anything else (specials,
    music, extras) returns ``None`` so the caller skips fulfillment.
    """
    item_type = item.get("Type", "")
    if item_type == "Episode":
        provider_ids = item.get("SeriesProviderIds") or {}
        media_type = "tv"
    elif item_type in ("Series", "Season", "Grouped"):
        provider_ids = item.get("ProviderIds") or {}
        media_type = "tv"
    elif item_type == "Movie" or item_type == "":
        provider_ids = item.get("ProviderIds") or {}
        media_type = "movie"
    else:
        return None

    raw = provider_ids.get("Tmdb") or provider_ids.get("tmdb")
    if not raw:
        return None
    try:
        return int(raw), media_type
    except (TypeError, ValueError):
        return None


async def try_auto_fulfill(item: dict, db: AsyncSession) -> int | None:
    """Mark a matching pending request as ``available`` and notify the
    requester.

    Returns the requester's ``user_id`` on success, ``None`` when no
    match was found (or the request had already been fulfilled, or the
    requester was GDPR-purged and there is nobody to notify).

    The status flip + notification insertion are wrapped in a SAVEPOINT
    so a flush-time integrity error cannot leave the request flipped
    without the bell — see Rules §24.
    """
    match = _emby_to_tmdb_match(item)
    if match is None:
        return None
    tmdb_id, media_type = match

    candidate = (
        await db.execute(
            select(MediaRequest)
            .where(
                MediaRequest.tmdb_id == tmdb_id,
                MediaRequest.media_type == media_type,
                MediaRequest.status.in_(ACTIONABLE_STATUSES),
            )
            .order_by(MediaRequest.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if candidate is None:
        return None

    request_id = candidate.id
    requester_id = candidate.user_id

    payload = {
        "tmdb_id": candidate.tmdb_id,
        "media_type": candidate.media_type,
        "title": candidate.title,
        "poster_url": candidate.poster_url,
        "request_id": candidate.id,
    }

    async with db.begin_nested():
        result = await db.execute(
            update(MediaRequest)
            .where(
                MediaRequest.id == request_id,
                MediaRequest.status.in_(ACTIONABLE_STATUSES),
            )
            .values(status=REQUEST_AVAILABLE_STATUS)
        )
        if result.rowcount == 0:
            return None
        if requester_id is not None:
            await notif_svc.create(
                db, requester_id, REQUEST_FULFILLED_NOTIF_TYPE, payload,
            )

    logger.info(
        f"[NOTIFICATIONS] auto-fulfilled request_id={request_id} "
        f"({media_type}:{tmdb_id})"
    )
    return requester_id
