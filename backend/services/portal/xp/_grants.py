"""
Direct XP grants: who may earn, the ledger and the daily caps.

Direct grants:
  - watch_movie:          10 XP  (Movie items only, ≥85% runtime, cooldown 24h)
  - watch_episode:         3 XP  (Episode items only, ≥85% runtime, cooldown 24h)
  - daily_login:           2 XP  (1x per calendar day)
  - request_created:       5 XP  (max 5/day)
  - achievement_unlocked: 20-100 (one-time per achievement, amount = ach.xp_reward)

Series completion, request approvals, login streaks and event participation
are rewarded through the achievement system (``completionist_*``,
``ambassador_*``, ``streak_days``, ``events_created``…) — they are NOT
granted by ``grant_xp`` directly.

Anti-abuse:
  - Unique constraint (user_id, action, reference) prevents double grants
  - Daily cap on request XP: 25 XP/day (5 requests)
"""
import logging
from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from models.user import User
from services.portal.admin_users_constants import SOURCE_EMBY

from ._levels import MIN_LEVEL, level_from_xp

logger = logging.getLogger("mediakeeper.portal.xp")

DAILY_REQUEST_XP_CAP = 25

# XP amounts per action.
# `achievement_unlocked` is omitted on purpose — its amount is supplied by
# the caller via ``xp_override`` (each achievement carries its own reward).
XP_TABLE = {
    "watch_movie": 10,
    "watch_episode": 3,
    "daily_login": 2,
    "request_created": 5,
}

# What ranks a player on the monthly leaderboard: what they did, not what they
# were rewarded. Listed by hand so a future reward never joins the ranking by
# default; trophy and admin XP still count towards the level.
ACTIVITY_XP_ACTIONS = ("watch_movie", "watch_episode", "daily_login", "request_created")

# A trophy adds one ledger row, found again under this action and its reference.
ACHIEVEMENT_XP_ACTION = "achievement_unlocked"


def achievement_xp_reference(achievement_id: str) -> str:
    return f"ach:{achievement_id}"


# Who earns XP and trophies, whatever triggers the grant: an active player (deactivating,
# expiring or deleting an account clears ``is_active``) linked to a media-server user;
# neither a local account nor a never-linked profile. Select User joined to UserProfile.
EARNING_ACCOUNT = and_(
    User.is_active.is_(True),
    UserProfile.source == SOURCE_EMBY,
    UserProfile.emby_user_id.is_not(None),
    UserProfile.emby_user_id != "",
)


async def account_earns(db: AsyncSession, user_id: int) -> bool:
    """Whether an account may earn XP and trophies (``EARNING_ACCOUNT``)."""
    stmt = select(User.id).join(UserProfile, UserProfile.user_id == User.id)
    return await db.scalar(stmt.where(User.id == user_id, EARNING_ACCOUNT)) is not None


async def grant_xp(
    db: AsyncSession,
    user_id: int,
    action: str,
    reference: str,
    xp_override: int | None = None,
) -> dict | None:
    """
    Attempt to grant XP for an action. Returns the grant details if
    successful, or None if the account may not earn (``account_earns``) or
    the grant is blocked by anti-abuse rules.

    The unique constraint (user_id, action, reference) is the primary
    dedup mechanism — if the exact same grant was already recorded,
    the INSERT fails silently and we return None.
    """
    base_xp = xp_override if xp_override is not None else XP_TABLE.get(action, 0)
    if base_xp <= 0:
        return None
    # Same rule as the trophy check, including for a request an admin files
    # on another account's behalf.
    if not await account_earns(db, user_id):
        return None

    # --- Apply active XP boost multipliers (Christmas, Halloween, etc.) ---
    from services.portal.xp_boost import get_active_multiplier
    multiplier = await get_active_multiplier(db, action)
    xp_amount = round(base_xp * multiplier) if multiplier != 1.0 else base_xp

    # --- Daily caps ---
    today_start = datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # No daily cap on watch XP — if someone watches 10h of movies,
    # they earned it. Anti-abuse is handled by the 85% runtime check
    # and the 24h cooldown per item in grant_watch_xp().

    if action == "request_created":
        today_req_xp = await _daily_xp_sum(db, user_id, today_start,
                                            ("request_created",))
        if today_req_xp >= DAILY_REQUEST_XP_CAP:
            return None

    # --- Insert (dedup via unique constraint) ---
    # The INSERT runs inside a SAVEPOINT so a duplicate (user_id, action,
    # reference) trips the unique constraint without invalidating the
    # outer transaction — callers keep the work they had pending in the
    # same session.
    try:
        async with db.begin_nested():
            db.add(XpLedger(
                user_id=user_id,
                action=action,
                reference=reference,
                xp=xp_amount,
            ))
            await db.flush()
    except IntegrityError:
        logger.debug("[XP] duplicate blocked: user=%s action=%s ref=%s", user_id, action, reference)
        return None

    # --- Update profile XP + level (row-locked to prevent concurrent-grant loss) ---
    # populate_existing: the caller often holds this profile already, and the
    # lock alone would leave its older XP in place to be overwritten.
    profile = (await db.execute(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )).scalar_one_or_none()

    leveled_up = False
    if profile:
        profile.xp = (profile.xp or 0) + xp_amount
        new_level = level_from_xp(profile.xp)
        leveled_up = new_level > (profile.level or MIN_LEVEL)
        profile.level = new_level
        db.add(profile)

    await db.commit()

    result = {
        "action": action,
        "xp": xp_amount,
        "total_xp": profile.xp if profile else xp_amount,
        "level": profile.level if profile else MIN_LEVEL,
        "leveled_up": leveled_up,
    }
    logger.info("[XP] granted %s XP to user=%s for %s ref=%s", xp_amount, user_id, action, reference)
    return result


async def grant_daily_login_xp(
    db: AsyncSession, user_id: int
) -> dict | None:
    """Grant daily login XP (max 1 per calendar day)."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return await grant_xp(db, user_id, "daily_login", today)


async def _daily_xp_sum(
    db: AsyncSession,
    user_id: int,
    today_start: datetime,
    actions: tuple[str, ...],
) -> int:
    """Sum XP granted today for the given action types."""
    result = await db.execute(
        select(func.coalesce(func.sum(XpLedger.xp), 0)).where(
            XpLedger.user_id == user_id,
            XpLedger.action.in_(actions),
            XpLedger.created_at >= today_start,
        )
    )
    return result.scalar() or 0
