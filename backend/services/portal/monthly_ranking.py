"""Final ranking of every finished month, rebuilt from the XP ledger.

Nothing is stored: a past month always follows the current rules and the
current exclusions, like the live leaderboard it must agree with.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.xp_ledger import XpLedger
from services.portal._leaderboard_helpers import excluded_from_leaderboard
from services.portal.achievements_utils import _coerce_utc
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

    Months are cut in UTC here, like the live leaderboard: a SQL ``extract()``
    would follow the time zone of the PostgreSQL session.
    """
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    stmt = select(XpLedger.user_id, XpLedger.created_at, XpLedger.xp).where(
        XpLedger.action.in_(ACTIVITY_XP_ACTIONS),
        XpLedger.created_at < month_start,
    )
    excluded_ids = await excluded_from_leaderboard(db)
    if excluded_ids:
        stmt = stmt.where(~XpLedger.user_id.in_(excluded_ids))

    totals: dict[tuple[int, int], dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for user_id, created_at, xp in (await db.execute(stmt)).all():
        moment = _coerce_utc(created_at)
        totals[(moment.year, moment.month)][user_id] += xp
    return {month: _ranked(xp_by_user) for month, xp_by_user in totals.items()}
