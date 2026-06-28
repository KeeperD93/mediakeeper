"""Ticket system for media issues."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from constants.notifications import NOTIF_TICKET_REPLIED, NOTIF_TICKET_RESOLVED
from models.user import User
from models.portal.ticket import Ticket, TicketReply
from models.portal.profile import UserProfile
from core.pagination import decode_cursor, build_cursor_response
from services.portal import strip_tags_and_trim
from services.portal._rank_tiers import tier_for_level
from services.portal.avatars import avatar_public_url
from services.portal.media_title_localize import localize_titles

logger = logging.getLogger("mediakeeper.portal.tickets")


async def create_ticket(
    db: AsyncSession, user_id: int, data: dict
) -> dict:
    ticket = Ticket(
        user_id=user_id,
        emby_item_id=data.get("emby_item_id"),
        series_emby_id=data.get("series_emby_id"),
        tmdb_id=data.get("tmdb_id"),
        media_title=strip_tags_and_trim(data["media_title"], 500),
        media_type=data["media_type"],
        selected_seasons=data.get("selected_seasons"),
        issue_type=data["issue_type"],
        priority=data.get("priority", "minor"),
        description=strip_tags_and_trim(data["description"], 2000),
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    logger.info("[TICKET] #%s by user_id=%s", ticket.id, user_id)

    await _notify_admins_new_ticket(db, ticket, requester_id=user_id)
    return {"success": True, "id": ticket.id}


async def _notify_admins_new_ticket(
    db: AsyncSession, ticket: Ticket, *, requester_id: int
) -> None:
    """Bell every active admin when a new ticket lands.

    The author is excluded so an admin who files their own ticket does
    not self-ping. Failures are swallowed — the ticket creation must
    not fail because of a notification side-effect.
    """
    from services.portal import notifications as notif_svc
    try:
        result = await db.execute(
            select(UserProfile.user_id)
            .where(UserProfile.role == "admin")
            .where(UserProfile.account_active.is_(True))
            .where(UserProfile.user_id != requester_id)
        )
        admin_ids = [row for row in result.scalars().all()]
        if not admin_ids:
            return
        await notif_svc.create_many(
            db, admin_ids, "ticket_created",
            {
                "ticket_id": ticket.id,
                "title": ticket.media_title,
                "tmdb_id": ticket.tmdb_id,
                "media_type": ticket.media_type,
                "issue_type": ticket.issue_type,
                "priority": ticket.priority,
                "requester_id": requester_id,
            },
        )
        await db.commit()
    except Exception as e:
        logger.warning("[TICKETS] notif new ticket failed: %s", e)


async def list_tickets(
    db: AsyncSession,
    user_id: int | None = None,
    *,
    status_filter: str | None = None,
    issue_types: list[str] | None = None,
    sort: str = "newest",
    cursor: str | None = None,
    limit: int = 25,
    page: int | None = None,
    locale: str = "fr",
) -> dict:
    # Ticket.id is monotonically allocated alongside created_at, so ordering
    # by id keeps pagination cheap while honouring the requested creation-time
    # direction. ``page`` switches to offset pagination (the ticket lists use
    # numbered pages); cursor stays the default for any other caller.
    order_clause = Ticket.id.asc() if sort == "oldest" else Ticket.id.desc()
    query = select(Ticket).order_by(order_clause)
    count_q = select(func.count(Ticket.id))

    if user_id:
        query = query.where(Ticket.user_id == user_id)
        count_q = count_q.where(Ticket.user_id == user_id)
    if status_filter:
        query = query.where(Ticket.status == status_filter)
        count_q = count_q.where(Ticket.status == status_filter)
    if issue_types:
        query = query.where(Ticket.issue_type.in_(issue_types))
        count_q = count_q.where(Ticket.issue_type.in_(issue_types))

    total = (await db.execute(count_q)).scalar() or 0

    if page is not None:
        rows = (await db.execute(query.offset((page - 1) * limit).limit(limit))).scalars().all()
        items = await localize_titles(db, [_serialize(t) for t in rows], locale, title_key="media_title")
        return {"items": items, "total": total, "page": page, "per_page": limit}

    cursor_data = decode_cursor(cursor)
    if cursor_data and cursor_data.get("id"):
        cursor_id = cursor_data["id"]
        query = query.where(Ticket.id > cursor_id if sort == "oldest" else Ticket.id < cursor_id)
    items = [_serialize(t) for t in (await db.execute(query.limit(limit))).scalars().all()]
    items = await localize_titles(db, items, locale, title_key="media_title")
    return build_cursor_response(items, total, limit)


async def get_ticket(db: AsyncSession, ticket_id: int, *, locale: str = "fr") -> dict | None:
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        return None
    replies = await _get_replies(db, ticket_id)
    # Pull every author + the ticket creator in one round-trip so the
    # premium thread can render avatars/role badges without N+1 fetches.
    # Filter out NULLs (FK ``SET NULL`` since migration 041) so the
    # ``IN (…)`` clause in ``_load_user_summaries`` doesn't waste a slot.
    actor_ids = {
        uid
        for uid in {ticket.user_id, *(r["user_id"] for r in replies)}
        if uid is not None
    }
    summaries = await _load_user_summaries(db, actor_ids)

    data = _serialize(ticket)
    requester = summaries.get(ticket.user_id) if ticket.user_id is not None else None
    data["requester"] = requester
    data["requester_deleted"] = ticket.user_id is None
    data["replies"] = [
        {
            **r,
            "author": summaries.get(r["user_id"]) if r["user_id"] is not None else None,
            "author_deleted": r["user_id"] is None,
        }
        for r in replies
    ]
    return (await localize_titles(db, [data], locale, title_key="media_title"))[0]


async def add_reply(
    db: AsyncSession,
    ticket_id: int,
    user_id: int,
    content: str,
    *,
    is_admin: bool = False,
) -> dict:
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        return {"error": "not_found"}
    if ticket.user_id != user_id and not is_admin:
        return {"error": "forbidden"}
    reply = TicketReply(
        ticket_id=ticket_id,
        user_id=user_id,
        content=strip_tags_and_trim(content, 2000),
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)

    # Notify the ticket owner only when someone else answered. The
    # owner's own replies don't trigger a bell for themselves. Skip if
    # the owner has been purged (FK ``SET NULL``); ``mk_notifications``
    # forbids ``user_id=NULL``.
    if ticket.user_id is not None and user_id != ticket.user_id:
        from services.portal import notifications as notif_svc
        try:
            await notif_svc.create(db, ticket.user_id, NOTIF_TICKET_REPLIED, {
                "ticket_id": ticket.id,
                "title": ticket.media_title,
                "tmdb_id": ticket.tmdb_id,
                "media_type": ticket.media_type,
            })
            await db.commit()
        except Exception as e:
            logger.warning("[TICKETS] notif reply failed: %s", e)

    return {"success": True, "id": reply.id}


async def auto_close_resolved_tickets(
    db: AsyncSession, *, after_days: int = 7
) -> int:
    """Move tickets that have been ``resolved`` for ``after_days`` days into
    ``closed``. Run by the background scheduler so users don't have to
    actively chase stale tickets — the bell already pinged them when the
    admin marked it resolved, the second transition is silent.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=after_days)
    # ``synchronize_session="fetch"`` resolves matching IDs via a SELECT and
    # expires only those rows in the active session, instead of asking the
    # SQLAlchemy evaluator to compare ``Ticket.updated_at`` against ``cutoff``
    # in Python. The evaluator path raises on SQLite (test backend) where
    # the column comes back tz-naive even for ``DateTime(timezone=True)``.
    result = await db.execute(
        update(Ticket)
        .where(Ticket.status == "resolved")
        .where(Ticket.updated_at < cutoff)
        .values(status="closed", updated_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session="fetch")
    )
    closed = result.rowcount or 0
    if closed:
        await db.commit()
        logger.info("[TICKET] auto-closed %s ticket(s) resolved >%sd ago", closed, after_days)
    return closed


async def update_ticket_status(
    db: AsyncSession, ticket_id: int, new_status: str
) -> dict:
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        return {"error": "not_found"}
    previous_status = ticket.status
    ticket.status = new_status
    db.add(ticket)
    await db.commit()

    # Only ping the user when the ticket moves into a terminal state —
    # intermediate changes (e.g. open → in_progress) would be noise.
    # The ``ticket.user_id`` guard skips the notif when the author has
    # been GDPR-purged (FK ``SET NULL`` since migration 041); inserting
    # into ``mk_notifications`` with ``user_id=None`` would violate the
    # NOT NULL constraint there.
    if (
        new_status in ("resolved", "closed")
        and previous_status != new_status
        and ticket.user_id is not None
    ):
        from services.portal import notifications as notif_svc
        try:
            await notif_svc.create(db, ticket.user_id, NOTIF_TICKET_RESOLVED, {
                "ticket_id": ticket.id,
                "title": ticket.media_title,
                "tmdb_id": ticket.tmdb_id,
                "media_type": ticket.media_type,
                "status": new_status,
            })
            await db.commit()
        except Exception as e:
            logger.warning("[TICKETS] notif status failed: %s", e)

    return {"success": True}


async def _get_replies(db: AsyncSession, ticket_id: int) -> list[dict]:
    result = await db.execute(
        select(TicketReply)
        .where(TicketReply.ticket_id == ticket_id)
        .order_by(TicketReply.id.asc())
    )
    return [{
        "id": r.id,
        "user_id": r.user_id,
        "content": r.content,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in result.scalars().all()]


async def _load_user_summaries(
    db: AsyncSession, user_ids: set[int]
) -> dict[int, dict]:
    """Return ``{user_id: {username, display_name, avatar_url, role}}``.

    Uses a single LEFT JOIN so users without a portal profile (edge case
    for legacy admin accounts) still resolve to a usable display_name
    falling back to the raw username.
    """
    if not user_ids:
        return {}
    result = await db.execute(
        select(User, UserProfile)
        .join(UserProfile, UserProfile.user_id == User.id, isouter=True)
        .where(User.id.in_(user_ids))
    )
    out: dict[int, dict] = {}
    for user, profile in result.all():
        avatar = None
        if profile:
            avatar = (
                avatar_public_url(profile.avatar_custom_path)
                if profile.avatar_custom_path
                else profile.avatar_url
            )
        level = (profile.level if profile and profile.level else 1)
        out[user.id] = {
            "user_id": user.id,
            "username": user.username,
            "display_name": (profile.display_name if profile else None) or user.username,
            "avatar_url": avatar,
            "role": profile.role if profile else "viewer",
            "level": level,
            "tier": tier_for_level(level),
        }
    return out


def _serialize(t: Ticket) -> dict:
    return {
        "id": t.id,
        "user_id": t.user_id,
        "emby_item_id": t.emby_item_id,
        "series_emby_id": t.series_emby_id,
        "tmdb_id": t.tmdb_id,
        "media_title": t.media_title,
        "media_type": t.media_type,
        "selected_seasons": t.selected_seasons,
        "issue_type": t.issue_type,
        "priority": t.priority,
        "description": t.description,
        "status": t.status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }
