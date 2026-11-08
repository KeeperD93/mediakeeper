"""What a correction takes back from one player, worked out without writing anything.

A trophy of the hour goes when it was unlocked before the zone was saved, was not handed
out by an admin, and its rule holds on the UTC clock but not on the saved one. The cascade
follows. Simulating and applying both plan through here, so they cannot disagree.
"""
import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession
from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from services.portal.achievements_utils import (
    _build_playback_user_filter,
    _coerce_utc,
)
from services.portal.playback_algorithms import session_spans
from services.portal.profile_decorations import stale_decoration_updates
from services.portal.xp import (
    ACHIEVEMENT_XP_ACTION,
    achievement_xp_reference,
    level_from_xp,
)

from ._cascade import Holdings, cascade
from ._context import AchievementInfo, Context, is_imported
from ._judge import HOUR_CONDITIONS, Judge, PlayerPlays

logger = logging.getLogger("mediakeeper.portal.zone_correction")


@dataclass
class PlayerPlan:
    user_id: int
    xp: int
    level: int
    # Trophy taken back -> the progress the pass would store on the saved clock.
    direct: dict[str, int] = field(default_factory=dict)
    cascade: dict[str, int] = field(default_factory=dict)
    imported: set[str] = field(default_factory=set)
    kept_nowhere: list[str] = field(default_factory=list)
    kept_gifts: list[str] = field(default_factory=list)
    xp_removed: int = 0
    decorations: dict = field(default_factory=dict)

    @property
    def removed(self) -> dict[str, int]:
        return {**self.direct, **self.cascade}

    @property
    def xp_after(self) -> int:
        return max(0, self.xp - self.xp_removed)

    @property
    def level_after(self) -> int:
        return level_from_xp(self.xp_after)


async def _player_plays(db: AsyncSession, ctx: Context, user_id: int) -> PlayerPlays:
    played = await _build_playback_user_filter(db, user_id)
    rows = (await db.execute(
        select(PlaybackSession).where(played, *ctx.excl_filters)
    )).scalars().all()
    emby_ids = sorted((await db.execute(
        select(PlaybackSession.user_id).distinct().where(played)
    )).scalars().all())
    sessions = (await db.execute(
        select(PlaybackSession.started_at, PlaybackSession.ended_at, PlaybackSession.session_key)
        .where(PlaybackSession.user_id.in_(emby_ids))
    )).all() if emby_ids else []
    return PlayerPlays(
        user_id=user_id,
        rows=list(rows),
        spans=session_spans((start, end) for start, end, _ in sessions),
        native_spans=session_spans((start, end) for start, end, key in sessions if not is_imported(key)),
        emby_ids=emby_ids,
    )


async def _judge_hour_trophies(
    db: AsyncSession, ctx: Context, plan: PlayerPlan, candidates: list[AchievementInfo],
) -> None:
    judge = Judge(db, ctx, await _player_plays(db, ctx, plan.user_id))
    for ach in candidates:
        met_utc = await judge.value(ach, ctx.utc) >= ach.threshold
        local = await judge.value(ach, ctx.local)
        if met_utc and local < ach.threshold:
            plan.direct[ach.id] = local
            if await judge.value(ach, ctx.utc, native=True) < ach.threshold:
                plan.imported.add(ach.id)
        elif not met_utc and local < ach.threshold:
            plan.kept_nowhere.append(ach.id)


async def plan_player(db: AsyncSession, ctx: Context, profile: UserProfile) -> PlayerPlan:
    user_id = profile.user_id
    plan = PlayerPlan(user_id=user_id, xp=profile.xp or 0, level=profile.level or 0)
    rows = (await db.execute(
        select(UserAchievement.achievement_id, UserAchievement.unlocked_at)
        .where(UserAchievement.user_id == user_id, UserAchievement.unlocked.is_(True))
    )).all()
    held = {achievement_id: _coerce_utc(unlocked_at) for achievement_id, unlocked_at in rows}
    gifts = {a for a in held if (user_id, a) in ctx.admin_gifts}

    # Unlocked once the zone was saved, a trophy was judged on its clock: never taken back here.
    hour_trophies = [
        ctx.achievements[a] for a, unlocked_at in sorted(held.items())
        if ctx.achievements[a].condition_type in HOUR_CONDITIONS
        and a not in PLACEHOLDER_IDS
        and (unlocked_at is None or unlocked_at < ctx.zone_saved_at)
    ]
    plan.kept_gifts = [ach.id for ach in hour_trophies if ach.id in gifts]
    candidates = [ach for ach in hour_trophies if ach.id not in gifts]
    if candidates:
        await _judge_hour_trophies(db, ctx, plan, candidates)

    references = {achievement_xp_reference(a): a for a in held}
    ledger = {
        references[reference]: xp
        for reference, xp in (await db.execute(
            select(XpLedger.reference, XpLedger.xp).where(
                XpLedger.user_id == user_id, XpLedger.action == ACHIEVEMENT_XP_ACTION,
            )
        )).all()
        if reference in references
    }
    outcome = cascade(
        Holdings(frozenset(held), plan.xp, ledger, ctx.achievements), set(plan.direct), gifts,
    )
    plan.cascade = outcome.removed
    plan.kept_nowhere += outcome.kept_nowhere
    plan.kept_gifts += outcome.kept_gifts
    if plan.removed:
        plan.xp_removed = sum(ledger.get(a, 0) for a in plan.removed)
        plan.decorations = stale_decoration_updates(profile, set(held) - set(plan.removed))
    return plan


async def plan_all(db: AsyncSession, ctx: Context) -> tuple[list[PlayerPlan], int]:
    """Every profile, deactivated ones included; a player whose planning fails is counted."""
    profiles = (await db.execute(select(UserProfile).order_by(UserProfile.user_id))).scalars().all()
    plans: list[PlayerPlan] = []
    failed = 0
    for profile in profiles:
        user_id = profile.user_id
        try:
            async with db.begin_nested():
                plans.append(await plan_player(db, ctx, profile))
        except Exception:
            logger.exception("[ZONE_CORRECTION] planning failed", extra={"user_id": user_id})
            failed += 1
    return plans, failed
