"""« For you » block of the Portal daily digest: what moved on the viewer's own
requests and tickets since they last caught up."""
import logging
from datetime import UTC, datetime

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.daily_digest import (
    FOR_YOU_LIMIT,
    FOR_YOU_REQUEST_APPROVED,
    FOR_YOU_REQUEST_AVAILABLE,
    FOR_YOU_TICKET_REPLY,
)
from constants.requests import REQUEST_APPROVED, REQUEST_AVAILABLE
from models.portal.request import MediaRequest
from models.portal.ticket import Ticket, TicketReply
from services.instance_time import to_local

logger = logging.getLogger("mediakeeper.portal.daily_digest")

_Dated = tuple[datetime, dict]


def _item(at: datetime, kind: str, title: str, **refs) -> _Dated:
    at = to_local(at, UTC)
    item = {
        "kind": kind, "title": title, "at": at.isoformat(),
        "tmdb_id": None, "media_type": None, "ticket_id": None,
    }
    return at, item | refs


async def _requests(db: AsyncSession, user_id: int, since: datetime, limit: int) -> list[_Dated]:
    # Requests have no approval date: an approved one is dated by its last update.
    at = case(
        (MediaRequest.status == REQUEST_AVAILABLE, MediaRequest.available_at),
        else_=MediaRequest.updated_at,
    )
    rows = await db.execute(
        select(
            MediaRequest.status, MediaRequest.title, MediaRequest.tmdb_id,
            MediaRequest.media_type, at.label("at"),
        )
        .where(
            MediaRequest.user_id == user_id,
            MediaRequest.status.in_((REQUEST_AVAILABLE, REQUEST_APPROVED)),
            at > since,
        )
        .order_by(at.desc())
        .limit(limit)
    )
    return [
        _item(
            row.at,
            FOR_YOU_REQUEST_AVAILABLE if row.status == REQUEST_AVAILABLE
            else FOR_YOU_REQUEST_APPROVED,
            row.title,
            tmdb_id=row.tmdb_id,
            media_type=row.media_type,
        )
        for row in rows.all()
    ]


async def _ticket_replies(
    db: AsyncSession, user_id: int, since: datetime, limit: int,
) -> list[_Dated]:
    # A reply without author comes from a purged account, so never from the viewer.
    last_reply = func.max(TicketReply.created_at)
    rows = await db.execute(
        select(Ticket.id, Ticket.media_title, last_reply.label("at"))
        .join(TicketReply, TicketReply.ticket_id == Ticket.id)
        .where(
            Ticket.user_id == user_id,
            or_(TicketReply.user_id.is_(None), TicketReply.user_id != user_id),
            TicketReply.created_at > since,
        )
        .group_by(Ticket.id, Ticket.media_title)
        .order_by(last_reply.desc())
        .limit(limit)
    )
    return [
        _item(row.at, FOR_YOU_TICKET_REPLY, row.media_title, ticket_id=row.id)
        for row in rows.all()
    ]


async def recent(
    db: AsyncSession, user_id: int, *, since: datetime, limit: int = FOR_YOU_LIMIT,
) -> list[dict]:
    """Newest first: requests now available or approved, tickets someone else answered."""
    since = since.astimezone(UTC)  # SQLite drops any other offset
    try:
        dated = (
            await _requests(db, user_id, since, limit)
            + await _ticket_replies(db, user_id, since, limit)
        )
    except Exception as e:  # noqa: BLE001
        logger.debug("[DIGEST] for you failed: %s", e)
        return []
    dated.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in dated[:limit]]
