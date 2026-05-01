"""Aggregate counters for the page-header banner + tag list.

Cheap enough to compute on every page mount at MK scale (a few
hundred users at most).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile

from .admin_users_serialize import now_utc


async def get_users_stats(db: AsyncSession) -> dict[str, Any]:
    """Returns total / active / inactive / expiring_soon / expired /
    deleted / online counts for the page header banner."""
    ref = now_utc()
    soon = ref + timedelta(days=7)

    async def _count(*conditions) -> int:
        stmt = select(func.count(UserProfile.id)).select_from(UserProfile).join(
            User, User.id == UserProfile.user_id,
        )
        for cond in conditions:
            stmt = stmt.where(cond)
        return (await db.execute(stmt)).scalar() or 0

    not_deleted = UserProfile.deleted_at.is_(None)
    total = await _count(not_deleted)
    active = await _count(
        not_deleted,
        UserProfile.account_active.is_(True),
        User.is_active.is_(True),
    )
    inactive = await _count(
        not_deleted,
        or_(UserProfile.account_active.is_(False), User.is_active.is_(False)),
    )
    expiring_soon = await _count(
        not_deleted,
        UserProfile.access_end_date.isnot(None),
        UserProfile.access_end_date > ref,
        UserProfile.access_end_date <= soon,
    )
    expired = await _count(
        not_deleted,
        UserProfile.access_end_date.isnot(None),
        UserProfile.access_end_date <= ref,
    )
    deleted = await _count(UserProfile.deleted_at.isnot(None))

    return {
        "total": total,
        "active": active,
        "inactive": inactive,
        "expiring_soon": expiring_soon,
        "expired": expired,
        "deleted": deleted,
    }


async def list_distinct_tags(db: AsyncSession) -> dict[str, Any]:
    """Flatten ``user_profiles.tags`` (JSON array) into a unique sorted
    list. We do the flattening in Python because a JSONB GIN-friendly
    query would lock us into PostgreSQL — the test suite runs SQLite."""
    rows = (await db.execute(
        select(UserProfile.tags)
        .where(UserProfile.tags.isnot(None))
        .where(UserProfile.deleted_at.is_(None))
    )).scalars().all()
    seen: set[str] = set()
    for tags in rows:
        if not isinstance(tags, list):
            continue
        for t in tags:
            if isinstance(t, str) and t.strip():
                seen.add(t.strip())
    return {"tags": sorted(seen)}
