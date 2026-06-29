"""Request creation path — locking, duplicate checks, quota gating,
resubmit reuse, auto-approve handling.

Extracted from ``requests.py`` to keep that file under 300 lines. The
``create_request`` symbol is re-exported from ``requests`` for
back-compat with existing callers.
"""
import logging
import zlib

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.request import MediaRequest
from services.portal.requests_blacklist import (
    is_media_available,
    is_media_blacklisted,
)
from services.portal.requests_quota import (
    current_month as _current_month,
    get_or_create_quota as _get_or_create_quota,
)

logger = logging.getLogger("mediakeeper.portal.requests")

_REQUEST_USER_LOCK_NS = 401


async def _acquire_request_creation_locks(
    db: AsyncSession,
    user_id: int,
    tmdb_id: int,
    media_type: str,
) -> None:
    """Serialize request creation in Postgres to avoid duplicate rows and
    quota races under concurrent clicks / retries.

    SQLite test runs ignore this path; production Postgres gains a
    transaction-scoped lock per user and per media key."""
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return

    media_lock_ns = zlib.crc32(media_type.encode("utf-8")) & 0x7FFFFFFF
    await db.execute(
        text("SELECT pg_advisory_xact_lock(:classid, :objid)"),
        {"classid": _REQUEST_USER_LOCK_NS, "objid": int(user_id)},
    )
    await db.execute(
        text("SELECT pg_advisory_xact_lock(:classid, :objid)"),
        {"classid": int(media_lock_ns), "objid": int(tmdb_id)},
    )


async def create_request(
    db: AsyncSession, user_id: int, data: dict, *, is_admin: bool = False
) -> dict:
    """Create a media request after checking:
      - media already in Emby (→ `already_available`)
      - media blacklisted (3 rejects, admin-only unblock) (→ `media_blacklisted`)
      - pending/approved request already open (→ `already_requested`)
      - user's monthly quota (→ `quota_exceeded`)
    """
    tmdb_id = data["tmdb_id"]
    media_type = data["media_type"]
    requested_seasons = data.get("requested_seasons")

    # Block pornographic requests for non-admins unless the instance allows
    # them. The TMDB keyword lookup only runs when the policy is restrictive
    # (default), so enabling adult requests adds zero per-request cost.
    if not is_admin:
        from services.portal.admin import get_portal_flag
        if not await get_portal_flag(db, "portal.allow_adult_requests"):
            from services.portal.adult_filter import has_adult_keyword
            from services.tmdb import TmdbUnavailable, get_keyword_ids
            try:
                keyword_ids = await get_keyword_ids(media_type, tmdb_id, db, strict=True)
            except TmdbUnavailable:
                # Fail closed: we cannot confirm the item is non-adult, so
                # refuse rather than risk letting restricted content through
                # while the policy is off.
                return {"error": "adult_check_unavailable"}
            if has_adult_keyword(keyword_ids):
                return {"error": "adult_requests_disabled"}

    # The "already_available" guard is binary for movies but wrong for
    # partially-available TV series: the user is asking specifically for
    # the missing seasons/episodes, which the EmbyTmdbIndex can't tell
    # apart. When the request carries a season payload, trust the UI —
    # it only lets the user tick episodes the library doesn't already
    # have. Movies still hit the simple available check.
    if not (media_type == "tv" and requested_seasons):
        if await is_media_available(db, tmdb_id, media_type):
            return {"error": "already_available"}

    if await is_media_blacklisted(db, tmdb_id, media_type):
        return {"error": "media_blacklisted"}

    await _acquire_request_creation_locks(db, user_id, tmdb_id, media_type)

    existing_active = await db.execute(
        select(MediaRequest).where(
            MediaRequest.tmdb_id == tmdb_id,
            MediaRequest.media_type == media_type,
            MediaRequest.status.in_(["pending", "approved", "available"]),
        )
    )
    if existing_active.scalar_one_or_none():
        # Release the advisory locks acquired above so Postgres doesn't
        # hold them for the rest of the request handler.
        await db.rollback()
        return {"error": "already_requested"}

    # Resubmission path: the *same user* has a previously-rejected request
    # for this item. Reuse the row, increment retry_count, reset status to
    # pending. Quota still charges on resubmit (it's a new ask).
    rejected_own = (
        await db.execute(
            select(MediaRequest).where(
                MediaRequest.user_id == user_id,
                MediaRequest.tmdb_id == tmdb_id,
                MediaRequest.media_type == media_type,
                MediaRequest.status == "rejected",
            )
        )
    ).scalar_one_or_none()

    quota = await _get_or_create_quota(db, user_id, commit=False, lock_row=True)
    current_month = _current_month()

    if quota.month != current_month:
        quota.month = current_month
        quota.used = 0

    if not is_admin and not quota.unlimited and quota.used >= quota.max_allowed:
        # Release the quota row lock + advisory locks so concurrent
        # users aren't serialised behind this caller.
        await db.rollback()
        return {"error": "quota_exceeded"}

    auto = quota.auto_approve

    if rejected_own:
        rejected_own.status = "approved" if auto else "pending"
        rejected_own.reject_reason = None
        rejected_own.auto_approved = auto
        rejected_own.retry_count = (rejected_own.retry_count or 0) + 1
        rejected_own.requested_seasons = data.get("requested_seasons")
        rejected_own.title = data["title"]
        rejected_own.year = data.get("year")
        rejected_own.poster_url = data.get("poster_url")
        rejected_own.backdrop_url = data.get("backdrop_url") or rejected_own.backdrop_url
        db.add(rejected_own)
        req = rejected_own
    else:
        req = MediaRequest(
            user_id=user_id,
            tmdb_id=data["tmdb_id"],
            media_type=data["media_type"],
            title=data["title"],
            year=data.get("year"),
            poster_url=data.get("poster_url"),
            backdrop_url=data.get("backdrop_url"),
            status="approved" if auto else "pending",
            auto_approved=auto,
            requested_seasons=data.get("requested_seasons"),
            requested_by_admin=data.get("requested_by_admin"),
        )
        db.add(req)

    if not is_admin and not quota.unlimited:
        quota.used += 1
    db.add(quota)

    await db.flush()

    await db.commit()
    await db.refresh(req)
    logger.info(
        "[REQUEST] #%s by user_id=%s (auto=%s, retry=%s)",
        req.id, user_id, auto, req.retry_count,
    )
    quota_info = None
    if not is_admin and not quota.unlimited:
        quota_info = {"used": quota.used, "max": quota.max_allowed}
    return {
        "success": True,
        "id": req.id,
        "auto_approved": auto,
        "retry_count": req.retry_count,
        "quota": quota_info,
    }
