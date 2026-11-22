"""The finished months ranked before and after a watch XP recalculation, in memory:
the months whose leader changes, and the Competitor tiers the new ranking justifies or
no longer justifies (those already unlocked stay)."""
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.leaderboard import LeaderboardPeriod
from models.portal.achievement import Achievement, UserAchievement
from services.instance_time import to_local
from services.portal._leaderboard_helpers import excluded_from_leaderboard
from services.portal._leaderboard_periods import period_bounds
from services.portal.achievements_checks_progression import (
    COMPETITOR_MIN_PLAYERS,
    COMPETITOR_POSITIONS,
)
from services.portal.monthly_ranking import MonthlyEntry, rank_months, ranking_rows

from ._context import Context
from ._plan import Plan

type Month = tuple[int, int]


@dataclass(frozen=True)
class MonthChanges:
    leaders_changed: tuple[str, ...]
    # Competitor tier id -> players: justified and not held yet (given at the next check),
    # held but no longer justified (kept).
    competitor_new: dict[str, int]
    competitor_unjustified: dict[str, int]


def _leaders(rankings: dict[Month, list[MonthlyEntry]]) -> dict[Month, frozenset[int]]:
    return {month: frozenset(e.user_id for e in entries if e.rank == 1) for month, entries in rankings.items()}


def _ranks(rankings: dict[Month, list[MonthlyEntry]]) -> dict[int, list[int]]:
    """Each player's rank in every month Competitor counts."""
    ranks: dict[int, list[int]] = {}
    for entries in rankings.values():
        if len(entries) >= COMPETITOR_MIN_PLAYERS:
            for entry in entries:
                ranks.setdefault(entry.user_id, []).append(entry.rank)
    return ranks


async def month_changes(db: AsyncSession, ctx: Context, plan: Plan) -> MonthChanges:
    before = period_bounds(LeaderboardPeriod.MONTH, to_local(ctx.as_of, ctx.zone)).start
    excluded = await excluded_from_leaderboard(db)
    rows = await ranking_rows(db, before, excluded)
    gone = {row.id for player in plan.players for row in player.deleted}
    current = rank_months(((row.user_id, row.created_at, row.xp) for row in rows), ctx.zone)
    recalculated = rank_months([
        *((row.user_id, row.created_at, row.xp) for row in rows if row.id not in gone),
        *(
            (t.user_id, t.at, t.xp) for player in plan.players for t in player.inserted
            if t.at < before and t.user_id not in excluded
        ),
    ], ctx.zone)

    leaders_now, leaders_after = _leaders(current), _leaders(recalculated)
    changed = sorted(m for m in leaders_now.keys() | leaders_after.keys() if leaders_now.get(m) != leaders_after.get(m))

    positions = dict(COMPETITOR_POSITIONS)
    tiers = (await db.execute(
        select(Achievement.id, Achievement.condition_type, Achievement.threshold)
        .where(Achievement.condition_type.in_(list(positions)))
    )).all()
    held = set((await db.execute(
        select(UserAchievement.user_id, UserAchievement.achievement_id).where(
            UserAchievement.achievement_id.in_([tier.id for tier in tiers]), UserAchievement.unlocked.is_(True),
        )
    )).all())
    ranks = _ranks(recalculated)
    new, unjustified = Counter(), Counter()
    for tier in tiers:
        holders = {user_id for user_id, tier_id in held if tier_id == tier.id}
        for user_id in holders | ranks.keys():
            justified = sum(rank <= positions[tier.condition_type] for rank in ranks.get(user_id, [])) >= tier.threshold
            if justified and user_id not in holders:
                new[tier.id] += 1
            elif not justified and user_id in holders:
                unjustified[tier.id] += 1
    return MonthChanges(
        leaders_changed=tuple(f"{year}-{month:02d}" for year, month in changed),
        competitor_new=dict(new),
        competitor_unjustified=dict(unjustified),
    )
