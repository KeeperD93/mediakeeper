"""The watch XP rows due, title by title, by the rule the collector pays with."""
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from constants.watch_xp_recalc import (
    SKIP_BEFORE_LEDGER,
    SKIP_COOLDOWN,
    SKIP_ERASED,
    SKIP_EXCLUDED,
    SKIP_NO_ACCOUNT,
    SKIP_NOT_EARNING,
    SKIP_PARALLEL,
)
from services.portal.exclusions import is_excluded
from services.portal.gdpr_erased import is_erased
from services.portal.xp import (
    WATCH_XP_COOLDOWN,
    WatchedTitle,
    boosted_watch_xp,
    completion_reference,
    watch_action,
    watch_xp_amount,
    watch_xp_eligible,
)
from services.portal.xp_boost import multiplier_at

from ._context import Context


@dataclass(frozen=True)
class Title:
    """A watched title (``PlaybackCompletion``) and who watched it on Emby."""

    watched: WatchedTitle
    emby_user_id: str
    emby_name: str
    item_name: str


@dataclass(frozen=True)
class Target:
    """A watch XP row due to the account ``user_id``; ``base`` is its XP before any bonus."""

    user_id: int
    title_id: int
    action: str
    reference: str
    runtime: int
    base: int
    xp: int
    at: datetime


@dataclass
class Targets:
    rows: list[Target] = field(default_factory=list)
    skipped: Counter = field(default_factory=Counter)
    # Titles paid to an account found by the Emby name, linked to another Emby user.
    namesakes: int = 0


def _refused(ctx: Context, title: Title) -> str | None:
    watched = title.watched
    if ctx.ledger_start is not None and watched.completed_at < ctx.ledger_start:
        return SKIP_BEFORE_LEDGER
    # By Emby id alone, like the collector: a namesake still earns.
    if is_erased(ctx.erased, title.emby_user_id, None):
        return SKIP_ERASED
    if is_excluded(title.item_name, list(ctx.exclusions)):
        return SKIP_EXCLUDED
    if not watch_xp_eligible(watched):
        return SKIP_PARALLEL
    return None


def _target(ctx: Context, user_id: int, watched: WatchedTitle) -> Target:
    action = watch_action(watched.item_type)
    multiplier = multiplier_at(ctx.events, action, watched.completed_at)
    return Target(
        user_id, watched.id, action, completion_reference(watched.item_id, watched.id), watched.runtime_seconds,
        watch_xp_amount(watched.runtime_seconds), boosted_watch_xp(watched.runtime_seconds, multiplier),
        watched.completed_at,
    )


def due_rows(ctx: Context, titles: list[Title], accounts: dict[tuple[str, str], int | None]) -> Targets:
    """The rows ``titles`` pay, taken in the order they counted as watched (date, then id).

    ``accounts`` maps an Emby id and name to the account the collector pays them to.
    """
    out = Targets()
    last_paid: dict[tuple[int, str], datetime] = {}
    for title in titles:
        reason = _refused(ctx, title)
        user_id = accounts.get((title.emby_user_id, title.emby_name)) if reason is None else None
        if reason is None and user_id is None:
            reason = SKIP_NO_ACCOUNT
        elif reason is None and user_id not in ctx.scope:
            reason = SKIP_NOT_EARNING
        watched = title.watched
        key = (user_id, watched.item_id)
        if reason is None and key in last_paid and watched.completed_at - last_paid[key] < WATCH_XP_COOLDOWN:
            reason = SKIP_COOLDOWN
        if reason is not None:
            out.skipped[reason] += 1
            continue
        if ctx.scope[user_id] != title.emby_user_id:
            out.namesakes += 1
        last_paid[key] = watched.completed_at
        out.rows.append(_target(ctx, user_id, watched))
    return out
