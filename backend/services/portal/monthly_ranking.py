"""Final ranking of every finished month, rebuilt from the XP ledger.

Nothing is stored: a past month always follows the current rules, the current
exclusions and the current time zone, like the live leaderboard it must agree with.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.leaderboard import LeaderboardPeriod
from models.portal.xp_ledger import XpLedger
from services.instance_time import get_instance_zone, to_local
from services.portal._leaderboard_helpers import excluded_from_leaderboard
from services.portal._leaderboard_periods import period_bounds
from services.portal.xp import ACTIVITY_XP_ACTIONS


@dataclass(frozen=True)
class MonthlyEntry:
    user_id: int
    xp: int
    rank: int


def _ranked(xp_by_user: dict[int, int]) -> list[MonthlyEntry]:
    """Best first; equal totals share a rank (1, 1, 3) and follow ``user_id``."""
    entries: list[MonthlyEntry] = []
    ordered = sorted(xp_by_user.items(), key=lambda item: (-item[1], item[0]))
    for position, (user_id, xp) in enumerate(ordered, start=1):
        rank = entries[-1].rank if entries and entries[-1].xp == xp else position
        entries.append(MonthlyEntry(user_id, xp, rank))
    return entries


async def finished_month_rankings(
    db: AsyncSession,
) -> dict[tuple[int, int], list[MonthlyEntry]]:
    """Return ``{(year, month): entries}`` for every month before the current one.

    Months are cut on the calendar of the instance, here like on the live leaderboard:
    a SQL ``extract()`` would follow the time zone of the PostgreSQL session.
    """
    zone = await get_instance_zone(db)
    month_start = period_bounds(LeaderboardPeriod.MONTH, to_local(datetime.now(UTC), zone)).start
    stmt = select(XpLedger.user_id, XpLedger.created_at, XpLedger.xp).where(
        XpLedger.action.in_(ACTIVITY_XP_ACTIONS),
        XpLedger.created_at < month_start,
    )
    excluded_ids = await excluded_from_leaderboard(db)
    if excluded_ids:
        stmt = stmt.where(~XpLedger.user_id.in_(excluded_ids))

    totals: dict[tuple[int, int], dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for user_id, created_at, xp in (await db.execute(stmt)).all():
        moment = to_local(created_at, zone)
        totals[(moment.year, moment.month)][user_id] += xp
    return {month: _ranked(xp_by_user) for month, xp_by_user in totals.items()}
