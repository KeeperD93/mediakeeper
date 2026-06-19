"""GDPR opt-in mode: settings, deletion request, scheduler purge.

All entry points are gated by the ``gdpr.enabled`` setting (default
``false``). Operators who do not need GDPR plumbing (small LAN
deployments) leave the toggle off and never see any of this surface;
the migration 040 schema changes are neutral on their own.

Settings touched here live in the generic ``settings`` key/value table
seeded by migration 040:

* ``gdpr.enabled``                  bool, default ``false``
* ``gdpr.account_purge_delay_days`` int (range 7-90), default ``30``
* ``gdpr.privacy_text_fr``          HTML, preset
* ``gdpr.privacy_text_en``          HTML, preset
* ``gdpr.dpo_contact``              free-form string, default empty

The deletion timestamps live on the ``users`` row
(``deletion_requested_at`` + ``pending_deletion_at``).

Snapshot collection and ZIP packaging live in private siblings
(``_gdpr_collect.py``, ``_gdpr_export.py``) so this module stays
under the 300-line cap. The names are re-exported here so callers
import a single public surface.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.settings import get_setting

# Public re-exports — keep the import surface stable for callers/tests.
from ._gdpr_collect import (  # noqa: F401
    collect_full_user_data as _collect_full_user_data,
)
from ._gdpr_export import (  # noqa: F401
    EXPORT_MAX_BYTES,
    build_export_zip,
)

logger = logging.getLogger("mediakeeper.portal.gdpr")


GDPR_ENABLED_KEY = "gdpr.enabled"
GDPR_DELAY_KEY = "gdpr.account_purge_delay_days"
GDPR_DPO_KEY = "gdpr.dpo_contact"
GDPR_PRIVACY_FR_KEY = "gdpr.privacy_text_fr"
GDPR_PRIVACY_EN_KEY = "gdpr.privacy_text_en"

DELAY_MIN_DAYS = 7
DELAY_MAX_DAYS = 90
DELAY_DEFAULT_DAYS = 30


def _parse_bool(raw: str | None) -> bool:
    if not raw:
        return False
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


# ─────────────────────────── Settings ───────────────────────────


async def is_gdpr_enabled(db: AsyncSession) -> bool:
    """Read the ``gdpr.enabled`` toggle live, no caching.

    Toggling the GDPR mode is rare but must take effect immediately
    across every gated endpoint and the scheduler — caching the value
    would create surprising windows where ``/me/export`` still works
    after the admin flipped the switch off.
    """
    raw = await get_setting(db, GDPR_ENABLED_KEY)
    return _parse_bool(raw)


async def get_purge_delay_days(db: AsyncSession) -> int:
    """Return the active purge delay clamped to the 7-90 range."""
    raw = await get_setting(db, GDPR_DELAY_KEY)
    if not raw:
        return DELAY_DEFAULT_DAYS
    try:
        n = int(raw)
    except (ValueError, TypeError):
        return DELAY_DEFAULT_DAYS
    return max(DELAY_MIN_DAYS, min(DELAY_MAX_DAYS, n))


# ─────────────────────────── Deletion request ───────────────────────────


async def submit_deletion_request(
    db: AsyncSession, user: User, *, delay_days: int,
) -> dict[str, Any]:
    """Stamp ``deletion_requested_at`` + ``pending_deletion_at`` on the user.

    Idempotent: if a request is already pending, return a payload with
    ``status="already_pending"`` so the caller can answer 409.
    """
    if user.pending_deletion_at is not None:
        return {
            "status": "already_pending",
            "deletion_requested_at": _iso(user.deletion_requested_at),
            "pending_deletion_at": _iso(user.pending_deletion_at),
        }

    now = datetime.now(timezone.utc)
    user.deletion_requested_at = now
    user.pending_deletion_at = now + timedelta(days=delay_days)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(
        "[GDPR] deletion request user_id=%s pending_at=%s delay=%sd",
        user.id, user.pending_deletion_at.isoformat(), delay_days,
    )
    return {
        "status": "pending",
        "deletion_requested_at": _iso(user.deletion_requested_at),
        "pending_deletion_at": _iso(user.pending_deletion_at),
    }


async def cancel_deletion_request(db: AsyncSession, user: User) -> bool:
    """Clear the deletion timestamps. Returns ``True`` if a pending
    request was actually cancelled, ``False`` if nothing was pending.
    """
    if user.deletion_requested_at is None and user.pending_deletion_at is None:
        return False
    user.deletion_requested_at = None
    user.pending_deletion_at = None
    db.add(user)
    await db.commit()
    logger.info("[GDPR] deletion request cancelled user_id=%s", user.id)
    return True


async def admin_cancel_deletion_request(
    db: AsyncSession,
    user: User,
    *,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Admin-side cancel: same effect as the user-side cancel but writes
    an audit row so the trail on the user drawer reflects the operator
    intervention. Returns ``{"error": "no_pending_request"}`` when the
    user has nothing pending — caller maps it to HTTP 404.
    """
    if user.deletion_requested_at is None and user.pending_deletion_at is None:
        return {"error": "no_pending_request"}

    from services.portal.admin_users_audit import record_audit
    from services.portal.admin_users_constants import (
        ACTION_USER_DELETION_REQUEST_CANCELLED,
    )

    user.deletion_requested_at = None
    user.pending_deletion_at = None
    db.add(user)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=user.id,
        action=ACTION_USER_DELETION_REQUEST_CANCELLED,
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    logger.info(
        "[GDPR] admin cancel deletion-request user_id=%s admin_user_id=%s",
        user.id, admin_user_id,
    )
    return {"ok": True}


async def refresh_pending_grace(
    db: AsyncSession, *, delay_days: int, commit: bool = True,
) -> int:
    """Re-stamp ``pending_deletion_at`` to ``now + delay_days`` for every user
    with a pending deletion, returning the number refreshed.

    Called when GDPR is re-enabled: a request that sat frozen while the feature
    was off would otherwise be purged instantly on the next run (its deadline
    long past). Refreshing the grace gives the member a fresh window to cancel.
    ``deletion_requested_at`` (the original intent timestamp) is left untouched.

    ``commit=False`` lets the caller batch this into the same transaction as the
    enable write, so a failed refresh rolls the toggle back too (atomic).
    """
    new_at = datetime.now(timezone.utc) + timedelta(days=delay_days)
    result = await db.execute(
        update(User)
        .where(User.pending_deletion_at.isnot(None))
        .values(pending_deletion_at=new_at)
    )
    if commit:
        await db.commit()
    count = result.rowcount or 0
    if count:
        logger.info("[GDPR] re-enabled: refreshed grace for %s pending deletion(s)", count)
    return count


# ─────────────────────────── Scheduler purge ───────────────────────────


async def purge_pending_deletions(db: AsyncSession) -> int:
    """Daily job: hard-delete every user whose grace period has lapsed.

    Early-returns when ``gdpr.enabled`` is false. Reads the delay from
    DB live (no cache). Relies on migration 040 / 041 FK rules:
    community-relevant tables (``chat_messages``, ``tickets``, ``news``,
    ``mk_events`` & friends) flip the FK to ``SET NULL`` so the rows
    survive anonymised; everything else stays ``CASCADE``.

    Before the FK ``SET NULL`` strips the link, every still-``scheduled``
    ``mk_event`` of the leaving user is moved to ``cancelled`` so it
    doesn't become a zombie nobody can edit. Failures of that side
    effect are logged and **must not** abort the purge — GDPR
    compliance prevails.
    """
    if not await is_gdpr_enabled(db):
        return 0

    now = datetime.now(timezone.utc)
    rows = (await db.execute(
        select(User).where(User.pending_deletion_at.isnot(None))
        .where(User.pending_deletion_at <= now)
    )).scalars().all()

    purged = 0
    for user in rows:
        await _cancel_scheduled_mk_events(db, user.id)
        logger.info(
            "[GDPR] purging user_id=%s username=%s scheduled_at=%s",
            user.id, user.username,
            user.pending_deletion_at.isoformat() if user.pending_deletion_at else None,
        )
        await db.delete(user)
        purged += 1

    if purged:
        await db.commit()
        logger.info("[GDPR] purge run complete: %s user(s) deleted", purged)
    return purged


async def _cancel_scheduled_mk_events(db: AsyncSession, user_id: int) -> None:
    """Cancel every ``scheduled`` ``mk_event`` created by ``user_id``
    so the FK ``SET NULL`` doesn't leave them un-actionable. Failures
    here are logged and swallowed — they must not block the upstream
    purge."""
    # Local imports to avoid a circular dependency: ``mk_events_crud``
    # transitively imports ``services.portal.notifications`` which can
    # touch this module during startup wiring.
    try:
        from models.portal.event import EventStatus, MKEvent
        from services.portal import mk_events_crud
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[GDPR] mk_events imports unavailable for user_id=%s: %s",
            user_id, exc,
        )
        return

    try:
        scheduled = (await db.execute(
            select(MKEvent.id).where(
                MKEvent.creator_user_id == user_id,
                MKEvent.status == EventStatus.SCHEDULED.value,
            )
        )).scalars().all()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[GDPR] scheduled mk_events lookup failed for user_id=%s: %s",
            user_id, exc,
        )
        return

    for event_id in scheduled:
        try:
            await mk_events_crud.cancel_event(
                db, event_id=event_id, creator_user_id=user_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[GDPR] auto-cancel of mk_event id=%s failed for user_id=%s: %s",
                event_id, user_id, exc,
            )
