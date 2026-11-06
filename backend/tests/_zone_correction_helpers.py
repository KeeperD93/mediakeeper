"""Shared setup for the tests of the trophy correction after a time zone is saved."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from models.playback_stats import PlaybackSession
from models.portal.achievement import UserAchievement
from models.portal.audit import AdminAuditLog
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.portal.admin_users_constants import ACTION_SYSTEM_TIMEZONE_CHANGED
from services.portal.xp import ACHIEVEMENT_XP_ACTION, achievement_xp_reference
from services.portal.zone_correction import _context
from services.settings import set_setting
from tests._portal_profile_helpers import make_portal_user

# The same month on every clock the tests use: at the turn of a month the tool refuses.
MID_MONTH = datetime(2026, 6, 15, 12, tzinfo=UTC)
# Winter: Paris is UTC+1. The zone is saved on the first of February.
ZONE_SAVED_AT = datetime(2026, 2, 1, 12, tzinfo=UTC)
BEFORE_SAVE = datetime(2026, 1, 20, tzinfo=UTC)
# 05:30 in UTC, 06:30 in Paris: the early bird in UTC only.
DAWN_UTC_ONLY = datetime(2026, 1, 5, 5, 30, tzinfo=UTC)
# 04:30 in UTC, 05:30 in Paris: the early bird in Paris.
DAWN_IN_PARIS = datetime(2026, 1, 6, 4, 30, tzinfo=UTC)


def at(*parts: int) -> datetime:
    return datetime(*parts, tzinfo=UTC)


def freeze(monkeypatch, moment: datetime = MID_MONTH) -> None:
    """The clock the tool reads the current month from."""
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment

    monkeypatch.setattr(_context, "datetime", _Frozen)


async def save_zone(db, name: str = "Europe/Paris", saved_at: datetime = ZONE_SAVED_AT) -> None:
    """The zone, and the trace its first save leaves."""
    await set_setting(db, INSTANCE_TIMEZONE_KEY, name, commit=False)
    db.add(AdminAuditLog(
        action=ACTION_SYSTEM_TIMEZONE_CHANGED, payload={"from": None, "to": name}, created_at=saved_at,
    ))
    await db.commit()


async def player(db, name: str, *, xp: int = 0, active: bool = True) -> int:
    user, profile = await make_portal_user(db, username=name)
    profile.xp = xp
    profile.account_active = active
    await db.commit()
    return user.id


def play(db, name: str, started: datetime, *, key: str | None = None, seconds: int = 60, **fields) -> None:
    db.add(PlaybackSession(
        session_key=key or f"{name}-{started.timestamp()}",
        user_id=f"emby-{name}",
        user_name=fields.pop("user_name", name),
        item_id=fields.pop("item_id", "item-1"),
        item_name="Test Movie",
        item_type=fields.pop("item_type", "Movie"),
        started_at=started,
        last_seen_at=started,
        ended_at=started + timedelta(seconds=seconds),
        measured=True,
        exclusive_seconds=seconds,
        **fields,
    ))


async def hold(db, user_id: int, achievement_id: str, xp: int = 40, unlocked_at: datetime = BEFORE_SAVE) -> None:
    """An unlocked trophy, its ledger row, and the XP it added to the profile."""
    db.add(UserAchievement(
        user_id=user_id, achievement_id=achievement_id, progress=1, unlocked=True,
        unlocked_at=unlocked_at, notified=True,
    ))
    if xp:
        db.add(XpLedger(
            user_id=user_id, action=ACHIEVEMENT_XP_ACTION,
            reference=achievement_xp_reference(achievement_id), xp=xp,
        ))
    profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalar_one()
    profile.xp = (profile.xp or 0) + xp
    await db.commit()


async def unlocked(db, user_id: int) -> set[str]:
    db.expire_all()
    return set((await db.execute(
        select(UserAchievement.achievement_id)
        .where(UserAchievement.user_id == user_id, UserAchievement.unlocked.is_(True))
    )).scalars().all())


async def profile_of(db, user_id: int) -> UserProfile:
    db.expire_all()
    return (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalar_one()
