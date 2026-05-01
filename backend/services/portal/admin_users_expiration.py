"""Automatic expiration of user accounts.

When ``UserProfile.access_end_date`` passes, this module deactivates the
account on both Emby (``Policy.IsDisabled = True`` + active sessions
killed) and MediaKeeper (``profile.account_active`` and ``user.is_active``
flipped off, JWTs invalidated). Triggered periodically by the scheduler
(``expire_users`` task) and as a defensive check during portal login.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from models.user import User
from services.emby.users import set_emby_user_enabled

from .admin_users_audit import record_audit
from .admin_users_constants import ACTION_USER_ACCESS_EXPIRED
from .admin_users_serialize import _aware, now_utc

logger = logging.getLogger("mediakeeper.portal.expiration")


async def _select_due_profiles(
    db: AsyncSession, ref: datetime
) -> list[tuple[UserProfile, User]]:
    """Profiles past their ``access_end_date`` that still need processing.

    A row is "still active" if at least one of ``account_active``,
    ``user.is_active`` or a non-True ``emby_is_disabled`` is set —
    matches the cleanup we are about to perform, so this query is also
    the idempotency guard."""
    stmt = (
        select(UserProfile, User)
        .join(User, User.id == UserProfile.user_id)
        .where(
            UserProfile.access_end_date.is_not(None),
            UserProfile.access_end_date <= ref,
            UserProfile.deleted_at.is_(None),
            or_(
                UserProfile.account_active.is_(True),
                User.is_active.is_(True),
                UserProfile.emby_is_disabled.is_(None),
                UserProfile.emby_is_disabled.is_(False),
            ),
        )
    )
    rows = (await db.execute(stmt)).all()
    return [(profile, user) for profile, user in rows]


async def _deactivate_one(
    db: AsyncSession,
    profile: UserProfile,
    user: User,
    *,
    ref: datetime,
    reason: str,
) -> dict[str, Any]:
    """Disable Emby (best-effort) + MediaKeeper, audit, no commit.

    The caller is expected to commit so a batch run gets a single
    transaction per profile (we already commit inside the helper to
    keep partial progress on error)."""
    emby_result: dict[str, Any] | None = None
    if profile.emby_user_id and profile.emby_is_disabled is not True:
        emby_result = await set_emby_user_enabled(
            db, profile.emby_user_id, enabled=False
        )
        if emby_result.get("ok"):
            profile.emby_is_disabled = True

    profile.account_active = False
    user.is_active = False
    profile.tokens_invalidated_at = ref
    db.add(profile)
    db.add(user)

    payload: dict[str, Any] = {
        "reason": reason,
        "access_end_date": _aware(profile.access_end_date).isoformat()
        if profile.access_end_date
        else None,
    }
    if emby_result is not None:
        payload["emby"] = emby_result

    await record_audit(
        db,
        admin_user_id=None,
        target_user_id=user.id,
        action=ACTION_USER_ACCESS_EXPIRED,
        payload=payload,
        commit=False,
    )
    await db.commit()

    return {
        "user_id": user.id,
        "username": user.username,
        "emby_disabled": bool(emby_result and emby_result.get("ok")),
        "emby_error": (emby_result or {}).get("error"),
    }


async def expire_due_users(db: AsyncSession) -> dict[str, Any]:
    """Process every profile whose ``access_end_date`` has passed.

    Returns ``{"processed": n, "emby_disabled": n, "errors": [...]}``."""
    ref = now_utc()
    due = await _select_due_profiles(db, ref)
    if not due:
        return {"processed": 0, "emby_disabled": 0, "errors": []}

    logger.info("[EXPIRE] %s profile(s) due for deactivation", len(due))

    processed = 0
    emby_disabled = 0
    errors: list[dict[str, Any]] = []

    for profile, user in due:
        try:
            res = await _deactivate_one(
                db, profile, user, ref=ref, reason="scheduler"
            )
            processed += 1
            if res["emby_disabled"]:
                emby_disabled += 1
            elif res["emby_error"]:
                errors.append(
                    {"user_id": user.id, "emby_error": res["emby_error"]}
                )
            logger.info(
                "[EXPIRE] user_id=%s username=%s emby_disabled=%s err=%s",
                user.id, user.username,
                res["emby_disabled"], res["emby_error"],
            )
        except Exception as e:
            await db.rollback()
            logger.exception(
                "[EXPIRE] failed for user_id=%s: %s", user.id, e
            )
            errors.append({"user_id": user.id, "error": str(e)})

    return {
        "processed": processed,
        "emby_disabled": emby_disabled,
        "errors": errors,
    }


async def expire_profile_if_due(
    db: AsyncSession, profile: UserProfile, user: User
) -> bool:
    """Just-in-time check used at portal login.

    Returns ``True`` if the profile was expired (and therefore
    deactivated), ``False`` otherwise. Safe to call on any profile —
    no-ops when ``access_end_date`` is null or in the future."""
    end = _aware(profile.access_end_date)
    if not end:
        return False
    ref = now_utc()
    if end > ref:
        return False
    if not (profile.account_active or user.is_active) and profile.emby_is_disabled is True:
        # Already deactivated, nothing left to do but the caller still
        # needs to know the account is expired.
        return True
    try:
        await _deactivate_one(
            db, profile, user, ref=ref, reason="login_gate"
        )
        logger.info(
            "[EXPIRE] just-in-time deactivation user_id=%s username=%s",
            user.id, user.username,
        )
    except Exception as e:
        await db.rollback()
        logger.exception(
            "[EXPIRE] just-in-time failed for user_id=%s: %s", user.id, e
        )
    return True
