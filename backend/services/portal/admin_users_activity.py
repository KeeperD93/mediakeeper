"""Activity counters consumed by the drawer Activity / Trophies tabs.

Returns lightweight aggregates only — the heavy lists (per-request,
per-trophy detail) are loaded by the existing user-facing endpoints
re-used in admin context with the target user id.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_user_activity_summary(
    db: AsyncSession, user_id: int
) -> dict[str, Any]:
    """Aggregate counters used by the drawer "Activity" tab.

    Reuses the existing portal models — none of the counts here are
    stored, they are recomputed on demand. Cheap enough at MK scale.
    """
    from models.portal.request import MediaRequest
    from models.portal.ticket import Ticket
    from models.portal.social import UserList, UserRating
    from models.portal.achievement import UserAchievement
    from models.portal.event import MKEvent, MKEventInvitation
    from models.portal.xp_ledger import XpLedger

    async def _count(model, attr: str = "user_id", **filters) -> int:
        col = getattr(model, attr)
        stmt = select(func.count()).where(col == user_id)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        return (await db.execute(stmt)).scalar() or 0

    async def _scalar(stmt) -> int:
        return (await db.execute(stmt)).scalar() or 0

    last_30_days = _now() - timedelta(days=30)

    requests = {
        "total": await _count(MediaRequest),
        "pending": await _count(MediaRequest, status="pending"),
        "approved": await _count(MediaRequest, status="approved"),
        "rejected": await _count(MediaRequest, status="rejected"),
        "available": await _count(MediaRequest, status="available"),
    }

    tickets = {
        "total": await _count(Ticket),
        "open": await _count(Ticket, status="open"),
        "closed": await _count(Ticket, status="closed"),
    }

    lists = {
        "total": await _count(UserList),
    }

    ratings = {
        "total": await _count(UserRating),
    }

    trophies = {
        "total": await _count(UserAchievement),
    }

    events = {
        "created": await _count(MKEvent, attr="creator_user_id"),
        "invited": await _count(MKEventInvitation),
    }

    xp_total = await _scalar(
        select(func.coalesce(func.sum(XpLedger.xp), 0))
        .where(XpLedger.user_id == user_id)
    )
    xp_30d = await _scalar(
        select(func.coalesce(func.sum(XpLedger.xp), 0))
        .where(XpLedger.user_id == user_id)
        .where(XpLedger.created_at >= last_30_days)
    )

    return {
        "requests": requests,
        "tickets": tickets,
        "lists": lists,
        "ratings": ratings,
        "trophies": trophies,
        "events": events,
        "xp": {"total": xp_total, "last_30_days": xp_30d},
    }
