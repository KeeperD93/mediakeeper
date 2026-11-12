"""Plan of a watch XP recalculation: the watch rows each player should hold, against
those they hold. A row already paid under the same reference and still due stays as
it is, its amount and date with it: the bonus it got is kept."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.watch_xp_recalc import LOST_NO_END, LOST_NO_STATS, LOST_NOT_DUE
from models.playback_stats import PlaybackCompletion, PlaybackSession
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.portal.achievements_utils import _coerce_utc
from services.portal.user_import import find_account_for_emby_user
from services.portal.xp import MIN_LEVEL, WatchedTitle, level_from_xp

from ._context import WATCH_ACTIONS, Context
from ._targets import Target, Title, due_rows


@dataclass(frozen=True)
class LedgerRow:
    id: int
    action: str
    reference: str
    xp: int
    at: datetime


@dataclass(frozen=True)
class PlayerPlan:
    user_id: int
    xp: int
    level: int
    kept: tuple[LedgerRow, ...]
    deleted: tuple[LedgerRow, ...]
    inserted: tuple[Target, ...]

    @property
    def changed(self) -> bool:
        return bool(self.deleted or self.inserted)

    @property
    def xp_after(self) -> int:
        """The profile XP less what goes, plus what comes: XP outside the ledger stays."""
        return max(0, self.xp - sum(row.xp for row in self.deleted) + sum(row.xp for row in self.inserted))

    @property
    def level_after(self) -> int:
        return level_from_xp(self.xp_after)

    @property
    def loses_all(self) -> bool:
        return bool(self.deleted) and not self.kept and not self.inserted


@dataclass(frozen=True)
class Plan:
    players: tuple[PlayerPlan, ...]
    # Every row due, in title order: what the fingerprint reads.
    targets: tuple[Target, ...]
    skipped: dict[str, int]
    namesakes: int
    lost: dict[str, int]


async def _titles(db: AsyncSession) -> list[Title]:
    rows = (await db.execute(
        select(
            PlaybackCompletion.id, PlaybackCompletion.item_id, PlaybackCompletion.item_type,
            PlaybackCompletion.runtime_seconds, PlaybackCompletion.exclusive_seconds,
            PlaybackCompletion.completed_at, PlaybackCompletion.user_id, PlaybackCompletion.user_name,
            PlaybackCompletion.item_name,
        ).order_by(PlaybackCompletion.completed_at, PlaybackCompletion.id)
    )).all()
    return [Title(WatchedTitle.of(row), row.user_id, row.user_name, row.item_name) for row in rows]


async def _accounts(db: AsyncSession, titles: list[Title]) -> dict[tuple[str, str], int | None]:
    """The account the collector pays each Emby user to, found the same way, never created."""
    found: dict[tuple[str, str], int | None] = {}
    for emby_id, name in dict.fromkeys((title.emby_user_id, title.emby_name) for title in titles):
        user = await find_account_for_emby_user(db, emby_username=name, emby_user_id=emby_id) if name else None
        found[(emby_id, name)] = user.id if user else None
    return found


async def _watch_rows(db: AsyncSession, user_ids: list[int]) -> dict[int, list[LedgerRow]]:
    held: dict[int, list[LedgerRow]] = defaultdict(list)
    for row in (await db.execute(
        select(XpLedger.id, XpLedger.user_id, XpLedger.action, XpLedger.reference, XpLedger.xp, XpLedger.created_at)
        .where(XpLedger.action.in_(WATCH_ACTIONS), XpLedger.user_id.in_(user_ids))
        .order_by(XpLedger.id)
    )).all():
        held[row.user_id].append(LedgerRow(row.id, row.action, row.reference, row.xp, _coerce_utc(row.created_at)))
    return held


def _diff(user_id: int, xp: int, level: int, held: list[LedgerRow], due: list[Target]) -> PlayerPlan:
    by_key = {(row.action, row.reference): row for row in held}
    due_keys = {(target.action, target.reference) for target in due}
    return PlayerPlan(
        user_id=user_id, xp=xp, level=level,
        kept=tuple(by_key[key] for key in ((t.action, t.reference) for t in due) if key in by_key),
        deleted=tuple(row for row in held if (row.action, row.reference) not in due_keys),
        inserted=tuple(t for t in due if (t.action, t.reference) not in by_key),
    )


async def _lost(db: AsyncSession, ctx: Context, plans: list[PlayerPlan], titles: list[Title]) -> dict[str, int]:
    """Why the players who lose all their watch XP have nothing left that pays."""
    lost = [ctx.scope[plan.user_id] for plan in plans if plan.loses_all]
    with_stats = set((await db.execute(
        select(PlaybackSession.user_id).where(PlaybackSession.user_id.in_(set(lost))).distinct()
    )).scalars())
    with_titles = {title.emby_user_id for title in titles}
    return dict(Counter(
        LOST_NO_STATS if emby_id not in with_stats else LOST_NO_END if emby_id not in with_titles else LOST_NOT_DUE
        for emby_id in lost
    ))


async def plan_all(db: AsyncSession, ctx: Context) -> Plan:
    """Every account of the scope that holds watch rows or that a due title reaches."""
    titles = await _titles(db)
    targets = due_rows(ctx, titles, await _accounts(db, titles))
    held = await _watch_rows(db, sorted(ctx.scope))
    due: dict[int, list[Target]] = defaultdict(list)
    for target in targets.rows:
        due[target.user_id].append(target)
    players = sorted(held.keys() | due.keys())
    profiles = {
        user_id: (xp or 0, level or MIN_LEVEL)
        for user_id, xp, level in (await db.execute(
            select(UserProfile.user_id, UserProfile.xp, UserProfile.level).where(UserProfile.user_id.in_(players))
        )).all()
    }
    plans = [_diff(user_id, *profiles[user_id], held.get(user_id, []), due.get(user_id, [])) for user_id in players]
    return Plan(
        players=tuple(plans),
        targets=tuple(targets.rows),
        skipped=dict(targets.skipped),
        namesakes=targets.namesakes,
        lost=await _lost(db, ctx, plans, titles),
    )
