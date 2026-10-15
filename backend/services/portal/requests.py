"""Media request system: list, vote, update status, serialize.

``create_request`` lives in ``requests_create.py`` (re-exported here for
back-compat). Blacklist helpers live in ``requests_blacklist.py``, quota
management (creation, monthly reset, snapshot) lives in
``requests_quota.py``.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from constants.notifications import (
    NOTIF_REQUEST_APPROVED,
    NOTIF_REQUEST_AVAILABLE,
    NOTIF_REQUEST_REJECTED,
)
from constants.requests import (
    REQUEST_APPROVED,
    REQUEST_AVAILABLE,
    REQUEST_PENDING,
    REQUEST_REJECTED,
)
from models.user import User
from models.portal.request import MediaRequest
from core.pagination import decode_cursor, build_cursor_response
from services.portal._rank_tiers import tier_for_level
from services.portal.profile_serializers import _resolve_avatar_url
from services.portal.requests_blacklist import maybe_blacklist_media
from services.portal.requests_quota import (
    current_month as _current_month,  # noqa: F401 — re-exported
    get_or_create_quota as _get_or_create_quota,  # noqa: F401 — re-exported
    get_user_quota,  # noqa: F401 — re-exported
)
from services.portal.requests_create import create_request  # noqa: F401
from services.portal.media_title_localize import localize_titles

logger = logging.getLogger("mediakeeper.portal.requests")

# Sort keys accepted by the admin queue (offset mode), mapped to ORDER BY
# clauses. Mirrors REQUEST_SORT in frontend/src/constants/requests.ts.
_REQUEST_SORTS = {
    "recent": (MediaRequest.id.desc(),),
    "oldest": (MediaRequest.id.asc(),),
    "title": (func.lower(MediaRequest.title).asc(), MediaRequest.id.desc()),
}


async def get_batch_status(
    db: AsyncSession,
    tmdb_ids: list[int],
    *,
    anonymize: bool = False,
) -> dict:
    """
    Return the most relevant request status per tmdb_id.

    Priority order (highest first):
        approved > pending > available > rejected

    ``rejected`` IS returned so MediaCard can surface the "Rejected"
    sash and swap the CTA to "Re-request" — but any fresher active
    status for the same item wins via the priority table.

    When ``anonymize`` is True, ``requested_by``, ``requested_by_deleted``
    and ``reject_reason`` are stripped so the caller can't tell who filed
    or moderated each request — only status and date stay visible. Used
    for non-admins when the Portal-wide ``anonymize_requests`` flag is
    on; admins always see the full payload to moderate.

    Archived requests are left out, like in the Requests lists.
    """
    if not tmdb_ids:
        return {}

    # Pick the "best" (highest priority) status per tmdb_id.
    PRIO = {REQUEST_APPROVED: 3, REQUEST_PENDING: 2, REQUEST_AVAILABLE: 1, REQUEST_REJECTED: 0}
    rows = await db.execute(
        select(MediaRequest, User.username)
        .join(User, MediaRequest.user_id == User.id, isouter=True)
        .where(
            MediaRequest.tmdb_id.in_(tmdb_ids),
            MediaRequest.status.in_(list(PRIO)),
            MediaRequest.archived_at.is_(None),
        )
        .order_by(MediaRequest.created_at.desc())
    )

    out: dict[str, dict] = {}
    for req, username in rows.all():
        key = str(req.tmdb_id)
        existing = out.get(key)
        new_prio = PRIO.get(req.status, 0)
        if existing and PRIO.get(existing["status"], 0) >= new_prio:
            continue
        entry: dict = {
            "status": req.status,
            "requested_at": req.created_at.isoformat() if req.created_at else None,
            "request_id": req.id,
            "retry_count": req.retry_count or 0,
        }
        if not anonymize:
            entry["reject_reason"] = (
                req.reject_reason if req.status == REQUEST_REJECTED else None
            )
            # ``user_id IS NULL`` after GDPR-purge (FK ``SET NULL`` since
            # migration 041). Flag it so the frontend renders an i18n
            # placeholder instead of ``user#None``.
            if req.user_id is None:
                entry["requested_by"] = None
                entry["requested_by_deleted"] = True
            else:
                entry["requested_by"] = username or f"user#{req.user_id}"
                entry["requested_by_deleted"] = False
        out[key] = entry
    return out


async def list_requests(
    db: AsyncSession,
    status_filter: str | None = None,
    cursor: str | None = None,
    limit: int = 25,
    *,
    page: int | None = None,
    sort: str = "recent",
    media_type: str | None = None,
    include_sensitive: bool = False,
    locale: str | None = None,
) -> dict:
    """List requests with optional status filter and pagination.

    Two pagination modes:
      - cursor (default): ``id < cursor`` ordered by id desc — the public
        ``/requests`` feed.
      - offset (when ``page`` is set): ``OFFSET (page-1)*limit`` honouring
        ``sort`` (recent/oldest/title) and ``media_type`` — the admin queue,
        which needs jump-to-page navigation plus server-side sort/filter
        across the whole set rather than just the loaded slice.

    When ``include_sensitive`` (admin path) is set, the response is
    enriched with the requester's display_name + avatar_url, and a missing
    poster or backdrop is backfilled from TMDB.

    Archived requests are left out: they only stay counted.
    """
    query = select(MediaRequest).where(MediaRequest.archived_at.is_(None))
    count_query = select(func.count(MediaRequest.id)).where(MediaRequest.archived_at.is_(None))

    if status_filter:
        query = query.where(MediaRequest.status == status_filter)
        count_query = count_query.where(MediaRequest.status == status_filter)
    if media_type:
        query = query.where(MediaRequest.media_type == media_type)
        count_query = count_query.where(MediaRequest.media_type == media_type)

    total = (await db.execute(count_query)).scalar() or 0

    if page is not None:
        order_by = _REQUEST_SORTS.get(sort, _REQUEST_SORTS["recent"])
        query = query.order_by(*order_by).offset((page - 1) * limit).limit(limit)
    else:
        query = query.order_by(MediaRequest.id.desc())
        cursor_data = decode_cursor(cursor)
        if cursor_data and cursor_data.get("id"):
            query = query.where(MediaRequest.id < cursor_data["id"])
        query = query.limit(limit)

    result = await db.execute(query)
    rows = list(result.scalars().all())

    requesters: dict[int, dict] = {}
    if include_sensitive and rows:
        await _backfill_images(db, rows)
        requesters = await _load_requester_profiles(
            db, {r.user_id for r in rows if r.user_id is not None},
        )

    items = [
        _serialize_request(
            r,
            include_sensitive=include_sensitive,
            requester=requesters.get(r.user_id) if include_sensitive else None,
        )
        for r in rows
    ]
    if locale:
        items = await localize_titles(db, items, locale)

    if page is not None:
        return {"items": items, "total": total, "page": page, "per_page": limit}
    return build_cursor_response(items, total, limit)


async def _backfill_images(
    db: AsyncSession, rows: list[MediaRequest],
) -> None:
    """Fill a missing poster or backdrop from TMDB: rows created before the
    backdrop column existed, or whose image was dropped at creation. One TMDB
    call per incomplete row, bounded by the page size (max 100)."""
    missing = [r for r in rows if not r.poster_url or not r.backdrop_url]
    if not missing:
        return
    from services.tmdb import get_media_detail
    changed = False
    for r in missing:
        try:
            detail = await get_media_detail(r.media_type, r.tmdb_id, db)
        except Exception:  # noqa: S112 -- intentional best-effort iteration, skip individual failure
            continue
        if not isinstance(detail, dict):
            continue
        if not r.poster_url and detail.get("poster"):
            r.poster_url = detail["poster"]
            changed = True
        if not r.backdrop_url and detail.get("backdrop"):
            r.backdrop_url = detail["backdrop"]
            changed = True
    if changed:
        await db.commit()


async def _load_requester_profiles(
    db: AsyncSession, user_ids: set[int],
) -> dict[int, dict]:
    """Return {user_id: {display_name, avatar_url, username}} for a batch."""
    if not user_ids:
        return {}
    from models.portal.profile import UserProfile
    result = await db.execute(
        select(User, UserProfile)
        .join(UserProfile, UserProfile.user_id == User.id, isouter=True)
        .where(User.id.in_(user_ids))
    )
    out: dict[int, dict] = {}
    for user, profile in result.all():
        level = (profile.level if profile and profile.level else 1)
        out[user.id] = {
            "username": user.username,
            "display_name": (profile.display_name if profile else None) or user.username,
            "avatar_url": _resolve_avatar_url(profile) if profile else None,
            "level": level,
            "tier": tier_for_level(level),
        }
    return out


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
      - `approved` → DM notification to the original requester; from
        `available` it silently undoes a wrong availability instead
      - `available` → DM notification (media landed in Emby); refused with
        ``not_in_library`` / ``library_check_failed`` while Emby does not
        verifiably hold the content, unless ``force`` (admin confirmed)
      - `rejected` (from pending or approved) → DM notification carrying the
        reason; if the media reaches BLACKLIST_REJECT_THRESHOLD total
        rejections across all requests, it's auto-added to the blacklist
        (hidden from every user-facing list until an admin unblocks it).
    """
    req = await db.get(MediaRequest, request_id)
    if not req:
        return {"error": "not_found"}
    undo_available = req.status == REQUEST_AVAILABLE and new_status == REQUEST_APPROVED
    if new_status == REQUEST_AVAILABLE and req.status != REQUEST_AVAILABLE:
        if not force:
            error = await _library_check_error(db, req)
            if error:
                return {"error": error}
        # Starts the auto-archive delay; re-marking an available request keeps it.
        req.available_at = datetime.now(timezone.utc)
    if undo_available:
        # The automatic flip redoes it once Emby really holds the content.
        req.available_at = None
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
        # Emby or TMDB unreachable: the admin decides, as for a missing title.
        logger.warning("[REQUEST] library check failed for request_id=%s", req.id, exc_info=True)
        return "library_check_failed"


def _serialize_request(
    r: MediaRequest,
    *,
    include_sensitive: bool = False,
    requester: dict | None = None,
) -> dict:
    data = {
        "id": r.id,
        "tmdb_id": r.tmdb_id,
        "media_type": r.media_type,
        "title": r.title,
        "year": r.year,
        "poster_url": r.poster_url,
        "backdrop_url": r.backdrop_url,
        "status": r.status,
        "auto_approved": r.auto_approved,
        "retry_count": r.retry_count or 0,
        "requested_seasons": r.requested_seasons,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
    if include_sensitive:
        data.update({
            "user_id": r.user_id,
            "reject_reason": r.reject_reason,
            "requested_by_admin": r.requested_by_admin,
            "approved_by": r.approved_by,
            "requester": requester,
            # ``True`` once the requester has been GDPR-purged (FK
            # ``SET NULL`` since migration 041). Lets the admin row
            # render an explicit "Deleted user" label.
            "requester_deleted": r.user_id is None,
        })
    return data
