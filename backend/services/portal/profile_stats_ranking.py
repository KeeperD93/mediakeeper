"""Ranking + user title + rank tier + mini-leaderboard for the profile page.

Ranking is based on XP earned during the current calendar month. The
premium /portal/leaderboard page consumes the richer
:func:`compute_leaderboard_only` payload that embeds viewer-aware stats
(rank when out of top-N, monthly totals, weekly delta, end-of-month
projection).
"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.portal._leaderboard_helpers import (
    build_entry,
    empty_payload,
    excluded_from_leaderboard,
    month_label,
)
# Re-exported for backward-compat with existing imports
# (services/portal/profile_stats.py + daily_digest_sources.py).
from services.portal._rank_tiers import (  # noqa: F401
    tier_for_level as tier_for_level,
    tier_for_title as tier_for_title,
    title_for_level as title_for_level,
)

logger = logging.getLogger("mediakeeper.portal.profile_stats")


LEADERBOARD_VISIBLE = 15  # Top 15 always shown in the profile mini-leaderboard.
LEADERBOARD_FULL_DEFAULT = 100  # Default cap for the dedicated /portal/leaderboard page.


async def compute_leaderboard_only(
    db: AsyncSession,
    *,
    limit: int = LEADERBOARD_FULL_DEFAULT,
    viewer_user_id: int | None = None,
    lang: str = "fr",
) -> dict:
    """Return top-N users for the current month + viewer-aware stats.

    Output dict: ``items`` (gc-lb-* rows), ``viewer_rank`` /
    ``viewer_entry`` (set when viewer is out of top-N) and ``stats``
    (month_label, total_players, total_xp_month, days_remaining,
    my_xp_month, my_delta_week, projected_end_rank).
    """
    try:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_start = (month_start - timedelta(days=1)).replace(day=1)
        if month_start.month == 12:
            next_month_start = month_start.replace(
                year=month_start.year + 1, month=1
            )
        else:
            next_month_start = month_start.replace(month=month_start.month + 1)
        days_remaining = max(0, (next_month_start - now).days)
        week_start = now - timedelta(days=7)

        excluded_ids = await excluded_from_leaderboard(db)

        current_stmt = (
            select(XpLedger.user_id, func.sum(XpLedger.xp).label("month_xp"))
            .where(XpLedger.created_at >= month_start)
        )
        if excluded_ids:
            current_stmt = current_stmt.where(~XpLedger.user_id.in_(excluded_ids))
        current_q = await db.execute(
            current_stmt.group_by(XpLedger.user_id).order_by(desc("month_xp"))
        )
        all_users = current_q.all()

        total_players = len(all_users)
        total_xp_month = sum((r.month_xp or 0) for r in all_users)
        leaders = all_users[:limit]

        if not leaders:
            payload = empty_payload(lang)
            payload["stats"]["total_players"] = total_players
            payload["stats"]["total_xp_month"] = total_xp_month
            payload["stats"]["days_remaining"] = days_remaining
            return payload

        prev_stmt = (
            select(XpLedger.user_id, func.sum(XpLedger.xp).label("month_xp"))
            .where(
                XpLedger.created_at >= prev_start,
                XpLedger.created_at < month_start,
            )
        )
        if excluded_ids:
            prev_stmt = prev_stmt.where(~XpLedger.user_id.in_(excluded_ids))
        prev_q = await db.execute(
            prev_stmt.group_by(XpLedger.user_id).order_by(desc("month_xp"))
        )
        prev_rank_by_user: dict[int, int] = {
            row.user_id: idx + 1 for idx, row in enumerate(prev_q.all())
        }

        leader_ids = [row.user_id for row in leaders]
        viewer_outside_top = (
            viewer_user_id is not None and viewer_user_id not in leader_ids
        )
        lookup_ids = list(leader_ids)
        if viewer_outside_top:
            lookup_ids.append(viewer_user_id)
        prof_rows = (await db.execute(
            select(UserProfile).where(UserProfile.user_id.in_(lookup_ids))
        )).scalars().all() if lookup_ids else []
        prof_by_id = {p.user_id: p for p in prof_rows}

        entry_kwargs = dict(
            prof_by_id=prof_by_id,
            prev_rank_by_user=prev_rank_by_user,
            viewer_user_id=viewer_user_id,
            lang=lang,
        )
        items = [
            build_entry(idx, row, **entry_kwargs)
            for idx, row in enumerate(leaders)
        ]

        viewer_rank: int | None = None
        viewer_entry: dict | None = None
        if viewer_outside_top:
            for idx, row in enumerate(all_users):
                if row.user_id == viewer_user_id:
                    viewer_rank = idx + 1
                    viewer_entry = build_entry(idx, row, **entry_kwargs)
                    break

        week_stmt = (
            select(XpLedger.user_id, func.sum(XpLedger.xp).label("week_xp"))
            .where(XpLedger.created_at >= week_start)
        )
        if excluded_ids:
            week_stmt = week_stmt.where(~XpLedger.user_id.in_(excluded_ids))
        week_q = await db.execute(week_stmt.group_by(XpLedger.user_id))
        week_by_user: dict[int, int] = {
            row.user_id: row.week_xp or 0 for row in week_q.all()
        }

        my_xp_month: int | None = None
        my_delta_week: int | None = None
        projected_end_rank: int | None = None
        if viewer_user_id is not None:
            my_xp_month = next(
                ((r.month_xp or 0) for r in all_users if r.user_id == viewer_user_id),
                0,
            )
            my_delta_week = week_by_user.get(viewer_user_id, 0)
            if total_players > 0:
                def _projected(uid: int, base_xp: int) -> float:
                    rate = (week_by_user.get(uid, 0) or 0) / 7
                    return float(base_xp or 0) + rate * days_remaining

                my_proj = _projected(viewer_user_id, my_xp_month or 0)
                better = sum(
                    1
                    for r in all_users
                    if r.user_id != viewer_user_id
                    and _projected(r.user_id, r.month_xp or 0) > my_proj
                )
                projected_end_rank = better + 1

        stats = {
            "month_label": month_label(now, lang),
            "total_players": total_players,
            "total_xp_month": total_xp_month,
            "days_remaining": days_remaining,
            "my_xp_month": my_xp_month,
            "my_delta_week": my_delta_week,
            "projected_end_rank": projected_end_rank,
        }

        return {
            "items": items,
            "viewer_rank": viewer_rank,
            "viewer_entry": viewer_entry,
            "stats": stats,
        }
    except Exception as e:
        logger.debug("[LEADERBOARD-ONLY] error: %s", e)
        return empty_payload(lang)


async def compute_ranking(
    db: AsyncSession, user: User, *, lang: str = "fr"
) -> dict:
    """Compute the viewer's monthly XP ranking + percentile + movement vs
    last month + a mini-leaderboard of the top ``LEADERBOARD_VISIBLE``
    players with tier info.

    When the current user is ranked below the visible window they're
    appended as an extra "me" row so the UI can show them next to the
    leaders (with their real rank). Each entry carries its own
    ``movement`` field so the UI can draw a green/red arrow + delta.

    Returns ``{position, total, percentile, movement, leaderboard}``.
    """
    rank_position = 0
    rank_total = 0
    rank_percentile = 0
    rank_movement = 0
    leaderboard: list[dict] = []

    try:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        excluded_ids = await excluded_from_leaderboard(db)

        all_stmt = (
            select(XpLedger.user_id, func.sum(XpLedger.xp).label("month_xp"))
            .where(XpLedger.created_at >= month_start)
        )
        if excluded_ids:
            all_stmt = all_stmt.where(~XpLedger.user_id.in_(excluded_ids))
        all_users_q = await db.execute(
            all_stmt.group_by(XpLedger.user_id).order_by(desc("month_xp"))
        )
        all_users = all_users_q.all()
        rank_total = len(all_users)

        for idx, row in enumerate(all_users):
            if row.user_id == user.id:
                rank_position = idx + 1
                break

        if rank_position > 0 and rank_total > 0:
            rank_percentile = max(1, round(100 * rank_position / rank_total))

        prev_start = (month_start - timedelta(days=1)).replace(day=1)
        prev_stmt = (
            select(XpLedger.user_id, func.sum(XpLedger.xp).label("month_xp"))
            .where(
                XpLedger.created_at >= prev_start,
                XpLedger.created_at < month_start,
            )
        )
        if excluded_ids:
            prev_stmt = prev_stmt.where(~XpLedger.user_id.in_(excluded_ids))
        prev_users_q = await db.execute(
            prev_stmt.group_by(XpLedger.user_id).order_by(desc("month_xp"))
        )
        prev_rank_by_user: dict[int, int] = {
            row.user_id: idx + 1 for idx, row in enumerate(prev_users_q.all())
        }
        prev_position = prev_rank_by_user.get(user.id, 0)
        if prev_position > 0 and rank_position > 0:
            rank_movement = prev_position - rank_position  # positive = improved

        leader_ids = [row.user_id for row in all_users[:LEADERBOARD_VISIBLE]]
        needs_me = (
            rank_position > LEADERBOARD_VISIBLE
            and user.id not in leader_ids
        )
        lookup_ids = list(leader_ids)
        if needs_me:
            lookup_ids.append(user.id)
        prof_rows = (await db.execute(
            select(UserProfile).where(UserProfile.user_id.in_(lookup_ids))
        )).scalars().all() if lookup_ids else []
        prof_by_id = {p.user_id: p for p in prof_rows}

        entry_kwargs = dict(
            prof_by_id=prof_by_id,
            prev_rank_by_user=prev_rank_by_user,
            viewer_user_id=user.id,
            lang=lang,
        )

        for idx, row in enumerate(all_users[:LEADERBOARD_VISIBLE]):
            leaderboard.append(build_entry(idx, row, **entry_kwargs))

        if needs_me:
            for idx, row in enumerate(all_users):
                if row.user_id == user.id:
                    leaderboard.append(build_entry(idx, row, **entry_kwargs))
                    break
    except Exception as e:
        logger.debug("[PROFILE] ranking error: %s", e)

    return {
        "position": rank_position,
        "total": rank_total,
        "percentile": rank_percentile,
        "movement": rank_movement,
        "leaderboard": leaderboard,
    }
