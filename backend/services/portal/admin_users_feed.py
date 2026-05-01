"""Per-user activity feeds consumed by the drawer Activity / Trophies tabs.

Each helper returns a flat list, latest-first, capped at a sensible
default. The admin can dig deeper via the user-facing endpoints if
needed — these feeds are scoped to a quick overview.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession


_TIER_NAMES = {1: "bronze", 2: "silver", 3: "gold", 4: "platinum", 5: "diamond", 6: "mythic"}
_RARITY_LABELS = {
    1: "common",
    2: "uncommon",
    3: "rare",
    4: "epic",
    5: "legendary",
    6: "mythic",
}


async def list_user_trophies(db: AsyncSession, user_id: int) -> dict[str, Any]:
    """Return unlocked + in-progress trophies for a user.

    Includes tier, rarity label and ``xp_reward`` so the admin drawer can
    surface "what did this trophy actually grant?" without an extra
    round-trip to the achievement catalogue.
    """
    from models.portal.achievement import Achievement, UserAchievement

    rows = (await db.execute(
        select(UserAchievement, Achievement)
        .join(Achievement, Achievement.id == UserAchievement.achievement_id)
        .where(UserAchievement.user_id == user_id)
        .order_by(desc(UserAchievement.unlocked), desc(UserAchievement.unlocked_at))
    )).all()

    unlocked: list[dict[str, Any]] = []
    in_progress: list[dict[str, Any]] = []
    for ua, ach in rows:
        item = {
            "id": ach.id,
            "name_key": ach.name_key,
            "icon": ach.icon,
            "category": ach.category,
            "progress": ua.progress,
            "threshold": ach.threshold,
            "tier": ach.tier,
            "tier_name": _TIER_NAMES.get(ach.tier, "bronze"),
            "rarity": _RARITY_LABELS.get(ach.tier, "common"),
            "xp_reward": ach.xp_reward,
            "secret": bool(ach.secret),
            "unlocked_at": ua.unlocked_at.isoformat() if ua.unlocked_at else None,
        }
        if ua.unlocked:
            unlocked.append(item)
        elif ua.progress > 0:
            in_progress.append(item)
    return {
        "unlocked": unlocked,
        "in_progress": in_progress,
        "unlocked_count": len(unlocked),
        "in_progress_count": len(in_progress),
    }


async def list_user_xp_ledger(
    db: AsyncSession, user_id: int, *, limit: int = 100
) -> dict[str, Any]:
    """Latest-first XP grants for a user."""
    from models.portal.xp_ledger import XpLedger

    rows = (await db.execute(
        select(XpLedger)
        .where(XpLedger.user_id == user_id)
        .order_by(desc(XpLedger.created_at))
        .limit(limit)
    )).scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "action": r.action,
                "reference": r.reference,
                "xp": r.xp,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


async def list_user_requests(
    db: AsyncSession, user_id: int, *, limit: int = 100
) -> dict[str, Any]:
    """Latest-first media requests for a user (title + status only)."""
    from models.portal.request import MediaRequest

    rows = (await db.execute(
        select(MediaRequest)
        .where(MediaRequest.user_id == user_id)
        .order_by(desc(MediaRequest.created_at))
        .limit(limit)
    )).scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "title": r.title,
                "year": r.year,
                "media_type": r.media_type,
                "status": r.status,
                "tmdb_id": r.tmdb_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


async def list_user_tickets(
    db: AsyncSession, user_id: int, *, limit: int = 100
) -> dict[str, Any]:
    """Latest-first problem tickets for a user (title + state only)."""
    from models.portal.ticket import Ticket

    rows = (await db.execute(
        select(Ticket)
        .where(Ticket.user_id == user_id)
        .order_by(desc(Ticket.created_at))
        .limit(limit)
    )).scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "title": r.media_title,
                "media_type": r.media_type,
                "issue_type": r.issue_type,
                "priority": r.priority,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }
