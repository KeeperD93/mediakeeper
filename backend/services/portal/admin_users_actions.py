"""Role / permissions / access window / Emby toggle.

Lifecycle (notes, tags, soft-delete, restore, RGPD, bulk) lives in
``admin_users_lifecycle`` to keep both files under the line cap.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile
from services.emby.users import set_emby_user_enabled

from .admin_users_constants import (
    ACTION_USER_ACCESS_EXTENDED,
    ACTION_USER_ACCESS_WINDOW,
    ACTION_USER_ACTIVATED,
    ACTION_USER_DEACTIVATED,
    ACTION_USER_EMBY_DISABLED,
    ACTION_USER_EMBY_ENABLED,
    ACTION_USER_PERMISSIONS_CHANGED,
    ACTION_USER_ROLE_CHANGED,
    PERMISSION_KEYS,
    ROLE_PRESETS,
    ROLES,
)
from .admin_users_audit import record_audit
from .admin_users_serialize import _aware, now_utc


def _apply_role_preset(profile: UserProfile, role: str) -> None:
    preset = ROLE_PRESETS.get(role)
    if not preset:
        return
    profile.role = role
    for key, value in preset.items():
        setattr(profile, key, value)


async def update_role(
    db: AsyncSession,
    profile: UserProfile,
    *,
    role: str,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if role not in ROLES:
        return {"error": "invalid_role"}
    previous = profile.role
    _apply_role_preset(profile, role)
    db.add(profile)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=profile.user_id,
        action=ACTION_USER_ROLE_CHANGED,
        payload={"from": previous, "to": role},
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True, "role": role}


async def update_permissions(
    db: AsyncSession,
    profile: UserProfile,
    *,
    permissions: dict[str, bool],
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    changed: dict[str, dict[str, bool]] = {}
    for key, value in permissions.items():
        if key not in PERMISSION_KEYS:
            continue
        previous = bool(getattr(profile, key))
        new_value = bool(value)
        if previous != new_value:
            changed[key] = {"from": previous, "to": new_value}
            setattr(profile, key, new_value)
    if not changed:
        return {"ok": True, "changed": {}}
    db.add(profile)
    if "can_chat" in changed:
        # Mirror the legacy column until it is dropped at v1.0.
        profile.chat_enabled = profile.can_chat
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=profile.user_id,
        action=ACTION_USER_PERMISSIONS_CHANGED,
        payload={"changed": changed},
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True, "changed": changed}


async def set_access_window(
    db: AsyncSession,
    profile: UserProfile,
    *,
    start: datetime | None,
    end: datetime | None,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    profile.access_start_date = start
    profile.access_end_date = end
    db.add(profile)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=profile.user_id,
        action=ACTION_USER_ACCESS_WINDOW,
        payload={
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
        },
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True}


async def extend_access(
    db: AsyncSession,
    profile: UserProfile,
    *,
    months: int,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if months <= 0 or months > 60:
        return {"error": "invalid_months"}
    # _aware() pins SQLite tz-naive datetimes to UTC so the comparison
    # below never raises in the test env.
    base = _aware(profile.access_end_date) or now_utc()
    if base < now_utc():
        base = now_utc()
    profile.access_end_date = base + timedelta(days=30 * months)
    if not profile.access_start_date:
        profile.access_start_date = now_utc()
    db.add(profile)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=profile.user_id,
        action=ACTION_USER_ACCESS_EXTENDED,
        payload={
            "months": months,
            "new_end": profile.access_end_date.isoformat(),
        },
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True, "access_end_date": profile.access_end_date.isoformat()}


async def set_account_active(
    db: AsyncSession,
    profile: UserProfile,
    user: User,
    *,
    active: bool,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    # An admin cannot deactivate their own account: the next request
    # would 401 and they would be locked out of MK with no escape hatch.
    if not active and admin_user_id is not None and admin_user_id == user.id:
        return {"error": "self_action_forbidden"}
    profile.account_active = active
    user.is_active = active
    db.add(profile)
    db.add(user)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=user.id,
        action=ACTION_USER_ACTIVATED if active else ACTION_USER_DEACTIVATED,
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True}


async def set_emby_account(
    db: AsyncSession,
    profile: UserProfile,
    *,
    enabled: bool,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if not profile.emby_user_id:
        return {"error": "no_emby_link"}
    res = await set_emby_user_enabled(db, profile.emby_user_id, enabled=enabled)
    # On success, mirror the new state into ``emby_is_disabled`` so the
    # list view reflects the change without a manual sync round-trip.
    if not res.get("error"):
        profile.emby_is_disabled = not enabled
        db.add(profile)
    # Always record an audit entry — successful toggles for traceability,
    # failed ones so an admin debugging Emby connectivity can see the
    # attempts in the user's audit tab.
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=profile.user_id,
        action=ACTION_USER_EMBY_ENABLED if enabled else ACTION_USER_EMBY_DISABLED,
        payload=({"error": res["error"]} if res.get("error") else None),
        ip=ip,
        user_agent=user_agent,
    )
    if res.get("error"):
        return res
    return {"ok": True}
