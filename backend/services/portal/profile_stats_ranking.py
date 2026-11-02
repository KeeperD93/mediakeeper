"""Ranking + user title + rank tier + mini-leaderboard for the profile page.

Ranking is based on activity XP earned during the current calendar month. The
premium /portal/leaderboard page consumes the richer
:func:`compute_leaderboard_only` payload, for one period, that embeds viewer-aware
stats (rank when out of top-N, totals and, on the month, weekly delta and
end-of-month projection).
"""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.leaderboard import LeaderboardPeriod
from models.portal.profile import UserProfile
from models.user import User
from services.portal._leaderboard_helpers import (
    activity_xp_by_user,
    build_entry,
    empty_payload,
    excluded_from_leaderboard,
    trophies_by_user_since,
    trophies_unlocked_since,
)
from services.portal._leaderboard_periods import (
    days_left_in_month,
    period_bounds,
    period_label,
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


async def _month_outlook(
    db: AsyncSession,
    excluded_ids: list[int],
    all_users: list,
    viewer_user_id: int,
    my_xp: int,
    now: datetime,
    days_remaining: int,
) -> tuple[int, int]:
    """Return the viewer's XP of the last 7 days and their projected end-of-month rank."""
    week_rows = await activity_xp_by_user(db, excluded_ids, now - timedelta(days=7))
    week_by_user: dict[int, int] = {row.user_id: row.total_xp for row in week_rows}

    def _projected(uid: int, base_xp: int) -> float:
        return float(base_xp) + week_by_user.get(uid, 0) / 7 * days_remaining

    my_proj = _projected(viewer_user_id, my_xp)
    better = sum(
        1
        for r in all_users
        if r.user_id != viewer_user_id and _projected(r.user_id, r.total_xp) > my_proj
    )
    return week_by_user.get(viewer_user_id, 0), better + 1


async def compute_leaderboard_only(
    db: AsyncSession,
    *,
    period: LeaderboardPeriod = LeaderboardPeriod.MONTH,
    limit: int = LEADERBOARD_FULL_DEFAULT,
    viewer_user_id: int | None = None,
    lang: str = "fr",
) -> dict:
    """Return top-N users for ``period`` + viewer-aware stats.

    Output dict: ``items`` (gc-lb-* rows), ``viewer_rank`` /
    ``viewer_entry`` (set when viewer is out of top-N) and ``stats``
    (period_label, total_players, total_xp, total_trophies, my_xp, and
    days_remaining, my_delta_week, projected_end_rank on the month only,
    None on the other periods).
    """
    try:
        now = datetime.now(UTC)
        bounds = period_bounds(period, now)
        days_remaining = (
            days_left_in_month(now) if period == LeaderboardPeriod.MONTH else None
        )

        excluded_ids = await excluded_from_leaderboard(db)

        all_users = await activity_xp_by_user(db, excluded_ids, bounds.start)

        total_players = len(all_users)
        total_xp = sum(r.total_xp for r in all_users)
        total_trophies = await trophies_unlocked_since(db, excluded_ids, bounds.start)
        leaders = all_users[:limit]

        if not leaders:
            payload = empty_payload(lang, period)
            payload["stats"]["total_players"] = total_players
            payload["stats"]["total_xp"] = total_xp
            payload["stats"]["total_trophies"] = total_trophies
            payload["stats"]["days_remaining"] = days_remaining
            return payload

        prev_rank_by_user: dict[int, int] | None = None
        if bounds.previous_start is not None:
            prev_rows = await activity_xp_by_user(
                db, excluded_ids, bounds.previous_start, bounds.start
            )
            prev_rank_by_user = {row.user_id: idx + 1 for idx, row in enumerate(prev_rows)}

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
            trophies_by_user=await trophies_by_user_since(db, lookup_ids, bounds.start),
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

        my_xp: int | None = None
        my_delta_week: int | None = None
        projected_end_rank: int | None = None
        if viewer_user_id is not None:
            my_xp = next(
                (r.total_xp for r in all_users if r.user_id == viewer_user_id),
                0,
            )
            if days_remaining is not None:
                my_delta_week, projected_end_rank = await _month_outlook(
                    db, excluded_ids, all_users, viewer_user_id, my_xp, now, days_remaining
                )

        stats = {
            "period_label": period_label(period, now, lang),
            "total_players": total_players,
            "total_xp": total_xp,
            "total_trophies": total_trophies,
            "days_remaining": days_remaining,
            "my_xp": my_xp,
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
        logger.error("[LEADERBOARD-ONLY] failed: %s", e)
        return empty_payload(lang, period)


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
        month = period_bounds(LeaderboardPeriod.MONTH, datetime.now(UTC))

        excluded_ids = await excluded_from_leaderboard(db)

        all_users = await activity_xp_by_user(db, excluded_ids, month.start)
        rank_total = len(all_users)

        for idx, row in enumerate(all_users):
            if row.user_id == user.id:
                rank_position = idx + 1
                break

        if rank_position > 0 and rank_total > 0:
            rank_percentile = max(1, round(100 * rank_position / rank_total))

        prev_rows = await activity_xp_by_user(db, excluded_ids, month.previous_start, month.start)
        prev_rank_by_user: dict[int, int] = {
            row.user_id: idx + 1 for idx, row in enumerate(prev_rows)
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
            trophies_by_user=await trophies_by_user_since(db, lookup_ids, month.start),
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
        logger.error("[PROFILE] ranking failed: %s", e)

    return {
        "position": rank_position,
        "total": rank_total,
        "percentile": rank_percentile,
        "movement": rank_movement,
        "leaderboard": leaderboard,
    }
