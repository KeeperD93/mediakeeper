"""Automatic request-quota recompute (engagement-scored).

A nightly job (see ``services/scheduler``) recomputes the monthly request
allowance of every user in ``mode='auto'`` from their last-30-day activity.
The cap rises quickly with activity and decays slowly once a user goes
inactive, clamped to the per-user ``[auto_min, auto_max]`` band. Manual-mode
and ``unlimited`` rows are never touched. See #59.

The scoring *shape* (weights / caps) lives here as code constants — those are
not knobs the operator tunes day-to-day. The operational knobs (window, band
defaults, grace, steps, on/off) come from the ``quota.auto.*`` Settings keys.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession
from models.portal.login_history import UserLoginHistory
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest, RequestQuota
from models.portal.social import UserList
from models.portal.ticket import Ticket
from models.user import User
from services.portal.admin_users_audit import record_audit
from services.portal.admin_users_constants import ACTION_USER_QUOTA_CHANGED
from services.portal.personal_utils import _playback_user_filter

logger = logging.getLogger("mediakeeper.portal.quota")

# Per-signal weight × per-signal cap. The cap stops a single, cheaply-farmed
# metric (junk tickets, throwaway lists) from inflating the allowance; Emby
# playback is the hardest signal to fake, so it weighs the most.
_WEIGHTS = {"play": 1.0, "login": 0.5, "request": 0.4, "list": 0.6, "ticket": 0.3}
_CAPS = {"play": 20, "login": 15, "request": 10, "list": 5, "ticket": 5}
# Score at which a user reaches the top of their band — set well below the
# theoretical max (36) so moderately-heavy use already maxes out.
_SCORE_FULL = 24.0
# Cap a user lands on when an admin flips them to auto (clamped to the band);
# the nightly job then drifts it from there. See admin.update_user_quota.
START_CAP = 5
# A row recomputed within this window is skipped on the next pass, so a reboot
# during the midnight hour cannot double-step a cap in the same night.
_RERUN_GUARD_HOURS = 20

# Settings defaults — overridable via the ``quota.auto.<key>`` Settings rows.
_INT_DEFAULTS = {
    "window_days": 30,
    "min": 2,
    "max": 15,
    "grace_days": 14,
    "up_step": 2,
    "down_step": 1,
}


def compute_score(counts: dict[str, int]) -> float:
    """Weighted, per-signal-capped engagement score."""
    return sum(_WEIGHTS[k] * min(counts.get(k, 0), _CAPS[k]) for k in _WEIGHTS)


def compute_target(score: float, lo: int, hi: int) -> int:
    """Map an engagement score onto the user's [lo, hi] band."""
    frac = min(score, _SCORE_FULL) / _SCORE_FULL if _SCORE_FULL else 0.0
    return round(lo + (hi - lo) * frac)


def next_cap(
    current: int,
    target: int,
    *,
    days_idle: int,
    grace_days: int,
    up_step: int,
    down_step: int,
    lo: int,
    hi: int,
) -> int:
    """Move ``current`` one asymmetric step toward ``target``, clamped to the
    band. Grants are quick; reductions only kick in once the user has been
    idle past the grace window (so a holiday does not shrink the allowance)."""
    if target > current:
        new = current + up_step
    elif target < current and days_idle >= grace_days:
        new = current - down_step
    else:
        new = current
    return max(lo, min(hi, new))


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _scalar(db: AsyncSession, stmt) -> int:
    return (await db.execute(stmt)).scalar() or 0


async def _gather(
    db: AsyncSession, user: User, profile: UserProfile | None, cutoff: datetime
) -> tuple[dict[str, int], datetime | None]:
    """Windowed per-signal counts + the user's most recent activity stamp."""
    uid = user.id
    play_filter = _playback_user_filter(user, profile)
    counts = {
        "login": await _scalar(db, select(func.count()).select_from(UserLoginHistory).where(
            UserLoginHistory.user_id == uid,
            UserLoginHistory.success.is_(True),
            UserLoginHistory.created_at >= cutoff,
        )),
        "request": await _scalar(db, select(func.count()).select_from(MediaRequest).where(
            MediaRequest.user_id == uid, MediaRequest.created_at >= cutoff,
        )),
        "list": await _scalar(db, select(func.count()).select_from(UserList).where(
            UserList.user_id == uid,
            UserList.is_deleted.is_(False),
            UserList.created_at >= cutoff,
        )),
        "ticket": await _scalar(db, select(func.count()).select_from(Ticket).where(
            Ticket.user_id == uid, Ticket.created_at >= cutoff,
        )),
        "play": await _scalar(db, select(func.count()).select_from(PlaybackSession).where(
            play_filter, PlaybackSession.started_at >= cutoff,
        )),
    }
    last_login = (await db.execute(
        select(func.max(UserLoginHistory.created_at)).where(
            UserLoginHistory.user_id == uid, UserLoginHistory.success.is_(True),
        )
    )).scalar()
    last_play = (await db.execute(
        select(func.max(PlaybackSession.started_at)).where(play_filter)
    )).scalar()
    stamps = [s for s in (_aware(last_login), _aware(last_play)) if s is not None]
    return counts, (max(stamps) if stamps else None)


async def _load_settings(db: AsyncSession) -> dict:
    from services.settings import get_setting

    cfg: dict = {}
    for key, default in _INT_DEFAULTS.items():
        # get_setting returns "" for an absent key (never None), so guard on
        # truthiness: an unset key takes the default directly instead of
        # routing int("") through the except.
        raw = await get_setting(db, f"quota.auto.{key}")
        try:
            cfg[key] = int(raw) if raw else default
        except (TypeError, ValueError):
            cfg[key] = default
    enabled = await get_setting(db, "quota.auto.enabled")
    # Absent (None or "") -> default ON; only an explicit false-y value disables.
    cfg["enabled"] = (
        True if not enabled
        else str(enabled).strip().lower() in ("1", "true", "yes", "on")
    )
    return cfg


async def recompute_auto_quotas(db: AsyncSession, *, now: datetime | None = None) -> dict:
    """Recompute every auto-mode quota from the activity window.

    Idempotent: a row touched within ``_RERUN_GUARD_HOURS`` is skipped, so a
    reboot inside the midnight window can't double-step. Audits (source=auto,
    actor=system) only when a cap actually changes.
    """
    cfg = await _load_settings(db)
    if not cfg["enabled"]:
        logger.debug("[QUOTA] auto recompute skipped (disabled)")
        return {"skipped": "disabled"}
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=cfg["window_days"])
    guard = now - timedelta(hours=_RERUN_GUARD_HOURS)

    quotas = (await db.execute(
        select(RequestQuota).where(RequestQuota.mode == "auto")
    )).scalars().all()

    processed = 0
    changed = 0
    for quota in quotas:
        if quota.unlimited:
            continue
        if quota.last_recomputed_at and _aware(quota.last_recomputed_at) >= guard:
            continue
        user = (await db.execute(
            select(User).where(User.id == quota.user_id)
        )).scalar_one_or_none()
        if user is None:
            continue
        profile = (await db.execute(
            select(UserProfile).where(UserProfile.user_id == quota.user_id)
        )).scalar_one_or_none()
        lo = _clamp(quota.auto_min, 1, 100)
        hi = max(lo, _clamp(quota.auto_max, 1, 100))
        counts, last_active = await _gather(db, user, profile, cutoff)
        score = compute_score(counts)
        target = compute_target(score, lo, hi)
        days_idle = (now - last_active).days if last_active else 10_000
        old_cap = quota.max_allowed
        new_cap = next_cap(
            old_cap, target,
            days_idle=days_idle, grace_days=cfg["grace_days"],
            up_step=cfg["up_step"], down_step=cfg["down_step"], lo=lo, hi=hi,
        )
        quota.last_recomputed_at = now
        db.add(quota)
        processed += 1
        if new_cap != old_cap:
            quota.max_allowed = new_cap
            await record_audit(
                db,
                admin_user_id=None,
                target_user_id=user.id,
                action=ACTION_USER_QUOTA_CHANGED,
                payload={
                    "changed": {"max_allowed": {"from": old_cap, "to": new_cap}},
                    "source": "auto",
                    "score": round(score, 1),
                    "target": target,
                    "direction": "grant" if new_cap > old_cap else "reduction",
                },
                commit=False,
            )
            changed += 1
    await db.commit()
    logger.info("[QUOTA] auto recompute: processed=%s changed=%s", processed, changed)
    return {"processed": processed, "changed": changed}
