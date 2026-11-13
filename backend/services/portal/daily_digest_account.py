"""Viewer blocks of the Portal daily digest: who is greeted, when the account
ends, and the XP earned yesterday."""
import logging
from datetime import UTC, datetime, tzinfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.daily_digest import EXPIRY_WARNING_DAYS
from constants.leaderboard import LeaderboardPeriod
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.instance_time import to_local
from services.portal._display_name import resolve_display_name
from services.portal._leaderboard_periods import period_bounds
from services.portal._rank_tiers import tier_for_level
from services.portal.admin_users_constants import ROLE_ADMIN
from services.portal.profile_serializers import _resolve_avatar_url
from services.portal.xp import MIN_LEVEL

logger = logging.getLogger("mediakeeper.portal.daily_digest")


def me(profile: UserProfile, name_lang: str) -> dict:
    """The viewer as the other players see them: the public name, never the login."""
    chosen = (
        None if (profile.display_name_must_set or profile.display_name is None)
        else profile.display_name
    )
    return {
        "display_name": resolve_display_name(
            chosen, profile.user_id, name_lang, is_admin=profile.role == ROLE_ADMIN,
        ),
        "avatar_url": _resolve_avatar_url(profile),
        "avatar_effect": profile.avatar_effect,
        "tier": tier_for_level(profile.level or MIN_LEVEL),
    }


def expiry(profile: UserProfile, *, now: datetime, zone: tzinfo) -> dict | None:
    """The end of the access when it comes within the warning window, else None.

    ``days_left`` counts calendar days of the instance, as the warning reads them.
    """
    end = to_local(profile.access_end_date, zone)
    if end is None or end <= now:
        return None
    days_left = (end.date() - to_local(now, zone).date()).days
    if days_left > EXPIRY_WARNING_DAYS:
        return None
    return {"ends_at": end.astimezone(UTC).isoformat(), "days_left": days_left}


async def xp_yesterday(db: AsyncSession, user_id: int, *, now: datetime, zone: tzinfo) -> int:
    """XP of every source the viewer earned on the instance's previous calendar day."""
    today = period_bounds(LeaderboardPeriod.TODAY, to_local(now, zone))
    try:
        total = (await db.execute(
            select(func.sum(XpLedger.xp)).where(
                XpLedger.user_id == user_id,
                XpLedger.created_at >= today.previous_start,
                XpLedger.created_at < today.start,
            )
        )).scalar()
    except Exception as e:  # noqa: BLE001
        logger.debug("[DIGEST] xp yesterday failed: %s", e)
        return 0
    return int(total or 0)
