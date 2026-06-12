"""Security-tab admin actions: reset password, force-logout, login history.

- ``reset_local_password`` only accepts profiles with ``source=local``
  (Emby owns the password for imported accounts). Returns the new
  plain password so the admin can hand it over once. The user is
  flagged ``must_change_password=True`` so they have to change it on
  first sign-in.
- ``force_logout`` stamps ``tokens_invalidated_at`` on the profile —
  ``api/portal/deps.py`` rejects every JWT issued before that timestamp.
- ``list_user_login_history`` reads the append-only
  ``user_login_history`` table for the Security tab feed.
"""
from __future__ import annotations

import secrets
import string
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.pagination import build_cursor_response, decode_cursor
from core.security import hash_password
from models.user import User
from models.portal.profile import UserProfile
from models.portal.login_history import UserLoginHistory

from .admin_users_audit import record_audit
from .admin_users_constants import (
    ACTION_USER_DISPLAY_NAME_RESET,
    ACTION_USER_FORCE_LOGOUT,
    ACTION_USER_PASSWORD_RESET,
    SOURCE_LOCAL,
)
from .admin_users_serialize import now_utc


_PASSWORD_ALPHABET = string.ascii_letters + string.digits


def _generate_password(length: int = 14) -> str:
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


async def reset_local_password(
    db: AsyncSession,
    profile: UserProfile,
    user: User,
    *,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if (profile.source or "") != SOURCE_LOCAL:
        return {"error": "not_local"}
    new_password = _generate_password()
    user.hashed_password = hash_password(new_password)
    user.must_change_password = True
    db.add(user)
    # Force every active session out at the same time so the old
    # password can never be re-used from a stale tab.
    profile.tokens_invalidated_at = now_utc()
    db.add(profile)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=user.id,
        action=ACTION_USER_PASSWORD_RESET,
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True, "password": new_password, "must_change_password": True}


async def force_logout(
    db: AsyncSession,
    profile: UserProfile,
    *,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    profile.tokens_invalidated_at = now_utc()
    db.add(profile)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=profile.user_id,
        action=ACTION_USER_FORCE_LOGOUT,
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True, "invalidated_at": profile.tokens_invalidated_at.isoformat()}


async def reset_display_name(
    db: AsyncSession,
    profile: UserProfile,
    *,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Flag the user so the "pick a username" overlay re-arms on next visit.

    The bypass for the 6-month rename cooldown is already wired into the
    user-facing patch path: when ``display_name_must_set`` is true, the
    lock check is skipped (see ``services.portal.profiles``).
    """
    profile.display_name_must_set = True
    db.add(profile)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=profile.user_id,
        action=ACTION_USER_DISPLAY_NAME_RESET,
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True}


async def list_user_login_history(
    db: AsyncSession, user_id: int, *, limit: int = 100, cursor: str | None = None
) -> dict[str, Any]:
    total = int((await db.execute(
        select(func.count(UserLoginHistory.id)).where(UserLoginHistory.user_id == user_id)
    )).scalar() or 0)
    q = select(UserLoginHistory).where(UserLoginHistory.user_id == user_id)
    decoded = decode_cursor(cursor) if cursor else None
    if decoded and decoded.get("id") is not None:
        q = q.where(UserLoginHistory.id < decoded["id"])
    rows = (await db.execute(
        q.order_by(UserLoginHistory.id.desc()).limit(limit)
    )).scalars().all()
    items = [
        {
            "id": r.id,
            "source": r.source,
            "success": r.success,
            "ip": r.ip,
            "user_agent": r.user_agent,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return build_cursor_response(items, total, limit, cursor_field="id")
