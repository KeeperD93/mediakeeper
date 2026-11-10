"""What every player of a correction run shares: the clocks, the months, the admin's gifts.

Read once per run and free of ORM objects, so it outlives the read-only transaction it
comes from and serves each per-player transaction of an apply, which reads that player's
gifts again under their lock.
"""
from dataclasses import dataclass
from datetime import UTC, datetime, tzinfo

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.leaderboard import LeaderboardPeriod
from constants.playback import IMPORTED_SESSION_KEY_PREFIXES
from constants.zone_correction import (
    MONTH_TURNING,
    ZONE_NOT_CHOSEN,
    ZONE_SAVED_AT_UNKNOWN,
)
from models.playback_stats import PlaybackSession
from models.portal.achievement import Achievement
from models.portal.audit import AdminAuditLog
from services.instance_time import get_instance_zone, to_local, zone_is_chosen
from services.portal._leaderboard_periods import period_bounds
from services.portal.achievements_checks_progression import COMPETITOR_MIN_PLAYERS
from services.portal.achievements_utils import _coerce_utc
from services.portal.admin_users_constants import (
    ACTION_DEBUG_ACHIEVEMENT_LOCKED,
    ACTION_DEBUG_ACHIEVEMENT_RESET_ALL,
    ACTION_DEBUG_ACHIEVEMENT_UNLOCKED,
    ACTION_SYSTEM_TIMEZONE_CHANGED,
)
from services.portal.exclusions import get_exclusion_filters
from services.portal.monthly_ranking import month_rankings
from services.portal.playback_algorithms import king_month_leaders, king_monthly_totals
from services.portal.playback_overlap import has_distinct_user_universe

type Month = tuple[int, int]


class ZoneCorrectionRefused(Exception):
    """The run cannot go on; ``code`` tells the client why."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AchievementInfo:
    id: str
    condition_type: str
    threshold: int
    name_key: str


@dataclass(frozen=True)
class Side:
    """One clock the rules are judged on: UTC, or the saved zone."""

    zone: tzinfo
    competitor_ranks: dict[int, list[int]]
    king_leaders: dict[Month, str | None]


@dataclass(frozen=True)
class Context:
    zone: tzinfo
    zone_saved_at: datetime
    achievements: dict[str, AchievementInfo]
    utc: Side
    local: Side
    # Leaders in UTC without the imported history: tells a removal that rests on it.
    king_leaders_native: dict[Month, str | None]
    universe: bool
    admin_gifts: frozenset[tuple[int, str]]
    excl_filters: list
    competitor_months: dict[str, int]
    king_months: dict[str, int]

    @property
    def zone_name(self) -> str:
        return getattr(self.zone, "key", "UTC")


def is_imported(session_key: str | None) -> bool:
    return bool(session_key) and session_key.startswith(IMPORTED_SESSION_KEY_PREFIXES)


async def _zone_saved_at(db: AsyncSession) -> datetime | None:
    """When the first zone was saved: the end of the UTC period."""
    rows = (await db.execute(
        select(AdminAuditLog.created_at, AdminAuditLog.payload)
        .where(AdminAuditLog.action == ACTION_SYSTEM_TIMEZONE_CHANGED)
        .order_by(AdminAuditLog.id)
    )).all()
    for created_at, payload in rows:
        if (payload or {}).get("from") is None:
            return _coerce_utc(created_at)
    return None


async def load_admin_gifts(db: AsyncSession, user_id: int | None = None) -> frozenset[tuple[int, str]]:
    """``(user_id, achievement_id)`` whose last admin event is a hand unlock, for one player
    when ``user_id`` is given."""
    stmt = (
        select(AdminAuditLog.action, AdminAuditLog.target_user_id, AdminAuditLog.payload)
        .where(AdminAuditLog.action.in_((
            ACTION_DEBUG_ACHIEVEMENT_UNLOCKED,
            ACTION_DEBUG_ACHIEVEMENT_LOCKED,
            ACTION_DEBUG_ACHIEVEMENT_RESET_ALL,
        )))
        .order_by(AdminAuditLog.id)
    )
    if user_id is not None:
        stmt = stmt.where(or_(
            AdminAuditLog.target_user_id == user_id,
            AdminAuditLog.action == ACTION_DEBUG_ACHIEVEMENT_RESET_ALL,
        ))
    rows = (await db.execute(stmt)).all()
    gifts: set[tuple[int, str]] = set()
    for action, target, payload in rows:
        achievement_id = (payload or {}).get("achievement_id")
        if action == ACTION_DEBUG_ACHIEVEMENT_RESET_ALL:
            gifts = {gift for gift in gifts if gift[1] != achievement_id}
        elif action == ACTION_DEBUG_ACHIEVEMENT_UNLOCKED:
            gifts.add((target, achievement_id))
        else:
            gifts.discard((target, achievement_id))
    return frozenset(gifts)


def _contested(rankings: dict) -> dict[Month, tuple[tuple[int, int], ...]]:
    """The months Competitor counts, each as its ``(user_id, rank)`` pairs."""
    return {
        month: tuple((entry.user_id, entry.rank) for entry in entries)
        for month, entries in rankings.items()
        if len(entries) >= COMPETITOR_MIN_PLAYERS
    }


def _ranks_by_user(months: dict[Month, tuple[tuple[int, int], ...]]) -> dict[int, list[int]]:
    ranks: dict[int, list[int]] = {}
    for pairs in months.values():
        for user_id, rank in pairs:
            ranks.setdefault(user_id, []).append(rank)
    return ranks


def _month_differences(utc: dict[Month, object], local: dict[Month, object]) -> dict[str, int]:
    """Months whose outcome differs between the clocks, and those only the zone has."""
    return {
        "changed": sum(utc.get(month) != local.get(month) for month in utc.keys() | local.keys()),
        "created": len(local.keys() - utc.keys()),
    }


async def build_context(db: AsyncSession) -> Context:
    zone = await get_instance_zone(db)
    if not zone_is_chosen(zone):
        raise ZoneCorrectionRefused(ZONE_NOT_CHOSEN)
    zone_saved_at = await _zone_saved_at(db)
    if zone_saved_at is None:
        raise ZoneCorrectionRefused(ZONE_SAVED_AT_UNKNOWN)

    # Each clock ranks the months it has finished, as the pass on it does. Until both are
    # in the same month, one of them has a month more to rank.
    now = datetime.now(UTC)
    local_now = to_local(now, zone)
    if (local_now.year, local_now.month) != (now.year, now.month):
        raise ZoneCorrectionRefused(MONTH_TURNING)
    contested_utc = _contested(await month_rankings(
        db, UTC, period_bounds(LeaderboardPeriod.MONTH, now).start,
    ))
    contested_local = _contested(await month_rankings(
        db, zone, period_bounds(LeaderboardPeriod.MONTH, local_now).start,
    ))

    sessions = (await db.execute(select(
        PlaybackSession.user_id, PlaybackSession.started_at,
        PlaybackSession.ended_at, PlaybackSession.session_key,
    ))).all()
    spans = [(user_id, started, ended) for user_id, started, ended, _ in sessions]
    native = [(user_id, started, ended) for user_id, started, ended, key in sessions if not is_imported(key)]
    king_utc = king_month_leaders(king_monthly_totals(spans, UTC))
    king_local = king_month_leaders(king_monthly_totals(spans, zone))

    achievements = {
        ach.id: AchievementInfo(ach.id, ach.condition_type, ach.threshold, ach.name_key)
        for ach in (await db.execute(select(Achievement))).scalars()
    }
    return Context(
        zone=zone,
        zone_saved_at=zone_saved_at,
        achievements=achievements,
        utc=Side(UTC, _ranks_by_user(contested_utc), king_utc),
        local=Side(zone, _ranks_by_user(contested_local), king_local),
        king_leaders_native=king_month_leaders(king_monthly_totals(native, UTC)),
        universe=await has_distinct_user_universe(db),
        admin_gifts=await load_admin_gifts(db),
        excl_filters=await get_exclusion_filters(db),
        competitor_months=_month_differences(contested_utc, contested_local),
        king_months=_month_differences(king_utc, king_local),
    )
