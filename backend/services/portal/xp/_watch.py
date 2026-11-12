"""
XP for watching a movie or an episode, paid when the title counts as watched.

  - 20 XP per hour of the title's runtime, rounded to the nearest, at least 1
  - only if the user watched at least 75 % of the runtime alone: a second title
    playing at the same time on the account earns nothing
  - once per title and account within 24 hours
  - dated when the title counted as watched, with the bonus events active
    then; the bonus stays in the amount written
"""
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.xp_ledger import XpLedger
from services.portal.xp_boost import boosted_xp, get_active_multiplier

from ._grants import _credit_locked, _refused, account_earns, locked_profile

logger = logging.getLogger("mediakeeper.portal.xp")

WATCH_XP_PER_HOUR = 20
MIN_WATCH_XP = 1
# Share of the runtime the user must have watched with no other title playing.
WATCH_XP_EXCLUSIVE_RATIO = 0.75
WATCH_XP_COOLDOWN = timedelta(hours=24)
# Trailers, music videos, live TV… earn nothing.
WATCH_XP_ACTIONS = {"Movie": "watch_movie", "Episode": "watch_episode"}
_SECONDS_PER_HOUR = 3600
# Between the item and the watched title's id in a reference; the former rule put a date there.
_COMPLETION_MARK = ":c"


@dataclass(frozen=True)
class WatchedTitle:
    """What watch XP reads from a watched title (``PlaybackCompletion``), as plain
    values: they outlive a rollback of the session."""

    id: int
    item_id: str
    item_type: str
    runtime_seconds: int
    exclusive_seconds: int
    completed_at: datetime

    @classmethod
    def of(cls, done) -> "WatchedTitle":
        at = done.completed_at
        return cls(
            done.id, done.item_id, done.item_type, done.runtime_seconds, done.exclusive_seconds,
            at.replace(tzinfo=UTC) if at.tzinfo is None else at,  # SQLite drops the offset
        )


def watch_xp_amount(runtime_seconds: int) -> int:
    """20 XP per hour of runtime, halves rounded up, at least 1 XP."""
    # Integer maths: ``round`` goes half to even and would pay 7.5 minutes 2 XP, not 3.
    rounded = (2 * runtime_seconds * WATCH_XP_PER_HOUR + _SECONDS_PER_HOUR) // (2 * _SECONDS_PER_HOUR)
    return max(MIN_WATCH_XP, rounded)


def boosted_watch_xp(runtime_seconds: int, multiplier: float) -> int:
    """What a watched title pays under a bonus ``multiplier``: still at least 1 XP,
    even under an event below ×1."""
    return max(MIN_WATCH_XP, boosted_xp(watch_xp_amount(runtime_seconds), multiplier))


def watch_action(item_type: str) -> str | None:
    """The ledger action of a title type; ``None`` for a type that earns nothing."""
    return WATCH_XP_ACTIONS.get(item_type)


def completion_reference(item_id: str, completion_id: int) -> str:
    """One ledger row per watched title, under a reference that never changes."""
    return f"{item_id}{_COMPLETION_MARK}{completion_id}"


def watch_xp_eligible(title: WatchedTitle) -> bool:
    """A movie or an episode watched alone for long enough."""
    return (
        watch_action(title.item_type) is not None
        and title.runtime_seconds > 0
        and title.exclusive_seconds >= title.runtime_seconds * WATCH_XP_EXCLUSIVE_RATIO
    )


async def grant_completion_xp(db: AsyncSession, user_id: int, title: WatchedTitle) -> dict | None:
    """Pay ``title``'s watch XP to ``user_id``, dated when it counted as watched.

    ``None`` when nothing is due. Once the profile is locked, every path commits.
    """
    if not watch_xp_eligible(title) or not await account_earns(db, user_id):
        return None
    action = watch_action(title.item_type)
    xp = boosted_watch_xp(title.runtime_seconds, await get_active_multiplier(db, action, title.completed_at))

    profile = await locked_profile(db, user_id)
    if profile is None:  # account deleted since ``account_earns``
        return await _refused(db)
    if await _paid_lately(db, user_id, action, title):
        logger.debug("[XP] watch cooldown: user=%s item=%s", user_id, title.item_id)
        return await _refused(db)
    reference = completion_reference(title.item_id, title.id)
    return await _credit_locked(db, profile, action, reference, xp, at=title.completed_at)


async def _paid_lately(db: AsyncSession, user_id: int, action: str, title: WatchedTitle) -> bool:
    """A watch row for the same title within 24 hours of it, before or after: a
    title caught up late still pays next to a later viewing. A row of the former
    rule has no upper bound: it was dated when the playback closed, after the end."""
    this_rule = XpLedger.reference.startswith(f"{title.item_id}{_COMPLETION_MARK}", autoescape=True)
    return await db.scalar(
        select(XpLedger.id).where(
            XpLedger.user_id == user_id,
            XpLedger.action == action,
            or_(
                XpLedger.reference == title.item_id,
                XpLedger.reference.startswith(f"{title.item_id}:", autoescape=True),
            ),
            XpLedger.created_at > title.completed_at - WATCH_XP_COOLDOWN,
            or_(~this_rule, XpLedger.created_at < title.completed_at + WATCH_XP_COOLDOWN),
        ).limit(1)
    ) is not None
