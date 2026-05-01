"""Request blacklist — 3-strike auto-block helpers + admin CRUD.

Extracted from ``requests.py`` (file-size rule). The 3-strike rule fires
from ``update_request_status`` in requests.py and delegates here.
"""
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest, RequestBlacklist
from models.portal.emby_tmdb_index import EmbyTmdbIndex

logger = logging.getLogger("mediakeeper.portal.requests_blacklist")

# Any media that accumulates this many rejections gets auto-blacklisted and
# vanishes from user-facing lists until an admin clears it.
BLACKLIST_REJECT_THRESHOLD = 3


async def is_media_available(
    db: AsyncSession, tmdb_id: int, media_type: str,
) -> bool:
    """True when the media already lives in the Emby library — requests
    must be blocked (user plays it directly instead)."""
    row = await db.execute(
        select(EmbyTmdbIndex.id).where(
            EmbyTmdbIndex.tmdb_id == tmdb_id,
            EmbyTmdbIndex.media_type == media_type,
        ).limit(1)
    )
    return row.scalar_one_or_none() is not None


async def is_media_blacklisted(
    db: AsyncSession, tmdb_id: int, media_type: str,
) -> bool:
    row = await db.execute(
        select(RequestBlacklist.id).where(
            RequestBlacklist.tmdb_id == tmdb_id,
            RequestBlacklist.media_type == media_type,
        ).limit(1)
    )
    return row.scalar_one_or_none() is not None


async def blacklisted_tmdb_ids(
    db: AsyncSession, media_type: str | None = None,
) -> set[int]:
    """Bulk lookup — used to filter discover/genre feeds in one DB round-trip."""
    stmt = select(RequestBlacklist.tmdb_id)
    if media_type:
        stmt = stmt.where(RequestBlacklist.media_type == media_type)
    rows = await db.execute(stmt)
    return {int(r[0]) for r in rows.all() if r[0] is not None}


async def reject_count(
    db: AsyncSession, tmdb_id: int, media_type: str,
) -> int:
    row = await db.execute(
        select(func.count(MediaRequest.id)).where(
            MediaRequest.tmdb_id == tmdb_id,
            MediaRequest.media_type == media_type,
            MediaRequest.status == "rejected",
        )
    )
    return int(row.scalar() or 0)


async def maybe_blacklist_media(
    db: AsyncSession, req: MediaRequest, admin_id: int,
) -> None:
    """When rejections for (tmdb_id, media_type) reach the threshold, add
    the media to ``request_blacklist`` with the full requester roster so
    the admin can review it later. Idempotent — one entry per media."""
    count = await reject_count(db, req.tmdb_id, req.media_type)
    if count < BLACKLIST_REJECT_THRESHOLD:
        return

    existing = await db.execute(
        select(RequestBlacklist.id).where(
            RequestBlacklist.tmdb_id == req.tmdb_id,
            RequestBlacklist.media_type == req.media_type,
        )
    )
    if existing.scalar_one_or_none():
        return

    rows = await db.execute(
        select(MediaRequest.user_id, User.username, UserProfile.display_name)
        .join(User, MediaRequest.user_id == User.id, isouter=True)
        .join(UserProfile, UserProfile.user_id == MediaRequest.user_id, isouter=True)
        .where(
            MediaRequest.tmdb_id == req.tmdb_id,
            MediaRequest.media_type == req.media_type,
        )
        .distinct()
    )
    requesters: list[dict] = []
    seen: set[int] = set()
    for user_id, username, display_name in rows.all():
        if user_id in seen:
            continue
        seen.add(user_id)
        requesters.append({
            "user_id": user_id,
            "display_name": display_name or username or f"user#{user_id}",
        })

    db.add(RequestBlacklist(
        tmdb_id=req.tmdb_id,
        media_type=req.media_type,
        title=req.title,
        year=req.year,
        poster_url=req.poster_url,
        requesters=requesters,
        reject_count=count,
        blocked_by=admin_id,
    ))
    logger.info(
        f"[BLACKLIST] {req.media_type}:{req.tmdb_id} auto-blocked after "
        f"{count} rejections ({len(requesters)} unique requester(s))"
    )


async def list_blacklist(db: AsyncSession) -> list[dict]:
    rows = await db.execute(
        select(RequestBlacklist).order_by(RequestBlacklist.blocked_at.desc())
    )
    out = []
    for bl in rows.scalars().all():
        out.append({
            "id": bl.id,
            "tmdb_id": bl.tmdb_id,
            "media_type": bl.media_type,
            "title": bl.title,
            "year": bl.year,
            "poster_url": bl.poster_url,
            "requesters": bl.requesters or [],
            "reject_count": bl.reject_count,
            "blocked_at": bl.blocked_at.isoformat() if bl.blocked_at else None,
        })
    return out


async def unblock_media(db: AsyncSession, blacklist_id: int) -> dict:
    bl = await db.get(RequestBlacklist, blacklist_id)
    if not bl:
        return {"error": "not_found"}
    tmdb_id, media_type = bl.tmdb_id, bl.media_type
    await db.delete(bl)
    # Reset existing rejected rows so the 3-strike counter restarts.
    # We flag them as ``rejected_cleared`` by nulling the reject_reason; the
    # status stays rejected for history but reject_count() still totals them.
    # Simpler: purge the rejected rows so the media gets a clean slate.
    from sqlalchemy import delete
    await db.execute(
        delete(MediaRequest).where(
            MediaRequest.tmdb_id == tmdb_id,
            MediaRequest.media_type == media_type,
            MediaRequest.status == "rejected",
        )
    )
    await db.commit()
    logger.info(f"[BLACKLIST] unblocked {media_type}:{tmdb_id} (+ purged rejected history)")
    return {"success": True}
