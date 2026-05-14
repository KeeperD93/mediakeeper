"""Shared helpers for the portal leaderboard.

Kept separate from :mod:`profile_stats_ranking` so the orchestrators
(``compute_ranking``, ``compute_leaderboard_only``) stay well under the
300-line file budget while sharing the exclusion query, the row →
entry builder and the month-label formatter.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from services.portal._display_name import resolve_display_name
from services.portal._rank_tiers import (
    tier_for_level,
    tier_for_title,
    title_for_level,
)
from services.portal.profile_serializers import _resolve_avatar_url


MONTH_LABELS_FR = [
    "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]
MONTH_LABELS_EN = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


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


def month_label(now: datetime, lang: str) -> str:
    """Format ``now`` as ``Mai 2026`` (FR) or ``May 2026`` (EN)."""
    table = MONTH_LABELS_FR if (lang or "fr").startswith("fr") else MONTH_LABELS_EN
    return f"{table[now.month]} {now.year}"


def build_entry(
    rank_idx: int,
    row,
    *,
    prof_by_id: dict,
    prev_rank_by_user: dict,
    viewer_user_id: int | None,
    lang: str,
) -> dict:
    """Build a leaderboard entry dict that matches the gc-lb-* schema."""
    prof = prof_by_id.get(row.user_id)
    p_level = prof.level if prof else 1
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
        "display_name": resolve_display_name(effective, row.user_id, lang),
        "avatar_url": _resolve_avatar_url(prof) if prof else None,
        "level": p_level,
        "tier": tier_for_level(p_level),
        "title_key": title_for_level(p_level),
        "month_xp": row.month_xp or 0,
        "selected_title": prof.selected_title if prof else None,
        "title_tier": tier_for_title(prof.selected_title if prof else None),
        "is_current_user": (
            viewer_user_id is not None and row.user_id == viewer_user_id
        ),
        "movement": movement,
    }


def empty_stats(lang: str) -> dict:
    """Stats payload returned when the leaderboard is empty or errored."""
    return {
        "month_label": month_label(datetime.now(timezone.utc), lang),
        "total_players": 0,
        "total_xp_month": 0,
        "days_remaining": 0,
        "my_xp_month": None,
        "my_delta_week": None,
        "projected_end_rank": None,
    }


def empty_payload(lang: str) -> dict:
    """Full empty payload — used by error paths and zero-leader runs."""
    return {
        "items": [],
        "viewer_rank": None,
        "viewer_entry": None,
        "stats": empty_stats(lang),
    }
