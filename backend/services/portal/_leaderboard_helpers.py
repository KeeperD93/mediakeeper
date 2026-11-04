"""Shared helpers for the portal leaderboard.

Kept separate from :mod:`profile_stats_ranking` so the orchestrators
(``compute_ranking``, ``compute_leaderboard_only``) stay well under the
300-line file budget while sharing the exclusion query, the activity XP
and trophy queries, the row → entry builder and the empty payload.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.leaderboard import LeaderboardPeriod
from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.portal._display_name import resolve_display_name
from services.portal._leaderboard_periods import period_label
from services.portal._rank_tiers import (
    tier_for_level,
    tier_for_title,
    title_for_level,
)
from services.portal.admin_users_constants import ROLE_ADMIN
from services.portal.profile_serializers import _resolve_avatar_url
from services.portal.xp import ACTIVITY_XP_ACTIONS


async def excluded_from_leaderboard(db: AsyncSession) -> list[int]:
    """Return user_ids that must never appear in the public ranking:

    - Non-Emby accounts (local-only profiles like the backoffice admin).
    - Deactivated MediaKeeper accounts (``account_active = False``).
    - Soft-deleted accounts (``deleted_at`` set).

    Emby admins and moderators DO appear: the ranking is open to every
    Emby user regardless of their MediaKeeper role.
    """
    rows = (await db.execute(
        select(UserProfile.user_id).where(
            (UserProfile.source != "emby")
            | (UserProfile.emby_user_id.is_(None))
            | (UserProfile.account_active.is_(False))
            | (UserProfile.deleted_at.isnot(None))
        )
    )).scalars().all()
    return list(rows)


async def activity_xp_by_user(
    db: AsyncSession,
    excluded_ids: list[int],
    start: datetime | None,
    end: datetime | None = None,
) -> list:
    """Return ``(user_id, total_xp)`` rows from ``start`` to ``end``, highest first.

    Without ``start``, the rows go back to the first one. Only activity counts:
    a trophy reward would feed the ranking that earned it, and a 0 XP Surprise
    row would add a player. Ties follow ``user_id`` to keep ranks stable between
    two displays.
    """
    stmt = select(XpLedger.user_id, func.sum(XpLedger.xp).label("total_xp")).where(
        XpLedger.action.in_(ACTIVITY_XP_ACTIONS),
    )
    if start is not None:
        stmt = stmt.where(XpLedger.created_at >= start)
    if end is not None:
        stmt = stmt.where(XpLedger.created_at < end)
    if excluded_ids:
        stmt = stmt.where(~XpLedger.user_id.in_(excluded_ids))
    result = await db.execute(
        stmt.group_by(XpLedger.user_id).order_by(desc("total_xp"), XpLedger.user_id)
    )
    return result.all()


async def trophies_unlocked_since(
    db: AsyncSession, excluded_ids: list[int], start: datetime | None
) -> int:
    """Count the trophies unlocked since ``start`` (ever, without it), excluded accounts left out."""
    stmt = select(func.count(UserAchievement.id)).where(UserAchievement.unlocked.is_(True))
    if start is not None:
        stmt = stmt.where(UserAchievement.unlocked_at >= start)
    if excluded_ids:
        stmt = stmt.where(~UserAchievement.user_id.in_(excluded_ids))
    return (await db.execute(stmt)).scalar_one()


async def trophies_by_user_since(
    db: AsyncSession, user_ids: list[int], start: datetime | None
) -> dict[int, int]:
    """Count the trophies each of ``user_ids`` unlocked since ``start`` (ever, without it).

    A player without any is absent from the result.
    """
    if not user_ids:
        return {}
    stmt = select(UserAchievement.user_id, func.count(UserAchievement.id)).where(
        UserAchievement.user_id.in_(user_ids),
        UserAchievement.unlocked.is_(True),
    )
    if start is not None:
        stmt = stmt.where(UserAchievement.unlocked_at >= start)
    rows = await db.execute(stmt.group_by(UserAchievement.user_id))
    return {user_id: count for user_id, count in rows.all()}


def build_entry(
    rank_idx: int,
    row,
    *,
    prof_by_id: dict,
    prev_rank_by_user: dict | None,
    trophies_by_user: dict[int, int],
    viewer_user_id: int | None,
    lang: str,
) -> dict:
    """Build a leaderboard entry dict that matches the gc-lb-* schema.

    ``movement`` is None when the period has no previous one to compare with.
    """
    prof = prof_by_id.get(row.user_id)
    p_level = prof.level if prof else 1
    movement = None
    if prev_rank_by_user is not None:
        prev_r = prev_rank_by_user.get(row.user_id, 0)
        movement = (prev_r - (rank_idx + 1)) if prev_r > 0 else 0
    effective = (
        None
        if prof is None or prof.display_name_must_set
        else prof.display_name
    )
    return {
        "rank": rank_idx + 1,
        "user_id": row.user_id,
        "display_name": resolve_display_name(
            effective, row.user_id, lang, is_admin=bool(prof) and prof.role == ROLE_ADMIN
        ),
        "avatar_url": _resolve_avatar_url(prof) if prof else None,
        "level": p_level,
        "tier": tier_for_level(p_level),
        "title_key": title_for_level(p_level),
        "period_xp": row.total_xp,
        "selected_title": prof.selected_title if prof else None,
        "title_tier": tier_for_title(prof.selected_title if prof else None),
        "is_current_user": (
            viewer_user_id is not None and row.user_id == viewer_user_id
        ),
        "movement": movement,
        "trophies_won": trophies_by_user.get(row.user_id, 0),
    }


def empty_stats(lang: str, period: LeaderboardPeriod, now: datetime) -> dict:
    """Stats payload returned when the leaderboard is empty or errored.

    ``now`` is on the clock of the instance: a failed query leaves no session to read it with.
    """
    return {
        "period_label": period_label(period, now, lang),
        "total_players": 0,
        "total_xp": 0,
        "total_trophies": 0,
        "days_remaining": None,
        "my_xp": None,
        "my_delta_week": None,
        "projected_end_rank": None,
    }


def empty_payload(lang: str, period: LeaderboardPeriod, now: datetime) -> dict:
    """Full empty payload — used by error paths and zero-leader runs."""
    return {
        "items": [],
        "viewer_rank": None,
        "viewer_entry": None,
        "stats": empty_stats(lang, period, now),
    }
