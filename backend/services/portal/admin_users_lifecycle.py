"""Notes / tags / soft-delete / restore / RGPD export / bulk runner.
Lifecycle = presence in the system + external view of the user's data.
Day-to-day toggles (role, permissions, access window, Emby) sit in
``admin_users_actions``."""
from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile

from .admin_users_actions import set_account_active, update_permissions, update_role
from .admin_users_audit import record_audit
from .admin_users_constants import (
    ACTION_USER_BULK,
    ACTION_USER_NOTES_UPDATED,
    ACTION_USER_RESTORED,
    ACTION_USER_RGPD_EXPORT,
    ACTION_USER_SOFT_DELETED,
    ACTION_USER_TAGS_UPDATED,
    BULK_ACTIONS,
    BULK_ACTIVATE,
    BULK_DEACTIVATE,
    BULK_DELETE,
    BULK_SET_PERMISSIONS,
    BULK_SET_ROLE,
    PERMISSION_KEYS,
    ROLES,
)
from .admin_users_serialize import now_utc


async def set_admin_notes(
    db: AsyncSession,
    profile: UserProfile,
    *,
    notes: str | None,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    profile.admin_notes = (notes or "").strip() or None
    db.add(profile)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=profile.user_id,
        action=ACTION_USER_NOTES_UPDATED,
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True}


async def set_tags(
    db: AsyncSession,
    profile: UserProfile,
    *,
    tags: list[str],
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    cleaned = sorted({t.strip()[:32] for t in tags if t and t.strip()})
    profile.tags = cleaned
    db.add(profile)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=profile.user_id,
        action=ACTION_USER_TAGS_UPDATED,
        payload={"tags": cleaned},
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True, "tags": cleaned}


async def soft_delete_user(
    db: AsyncSession,
    profile: UserProfile,
    user: User,
    *,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    # Self-deletion would lock the admin out of MK with no recovery
    # path. Refuse explicitly so the UI can surface a clear error.
    if admin_user_id is not None and admin_user_id == user.id:
        return {"error": "self_action_forbidden"}
    if profile.deleted_at is not None:
        return {"error": "already_deleted"}
    profile.deleted_at = now_utc()
    profile.deleted_by_user_id = admin_user_id
    profile.account_active = False
    user.is_active = False
    profile.tokens_invalidated_at = user.tokens_invalidated_at = profile.deleted_at  # revoke any JWT minted before the disable on both auth scopes
    db.add(profile)
    db.add(user)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=user.id,
        action=ACTION_USER_SOFT_DELETED,
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True}


async def restore_user(
    db: AsyncSession,
    profile: UserProfile,
    user: User,
    *,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if profile.deleted_at is None:
        return {"error": "not_deleted"}
    profile.deleted_at = None
    profile.deleted_by_user_id = None
    profile.account_active = True
    user.is_active = True
    db.add(profile)
    db.add(user)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=user.id,
        action=ACTION_USER_RESTORED,
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True}


async def export_user_data_rgpd(
    db: AsyncSession,
    profile: UserProfile,
    user: User,
    *,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Snapshot every record we keep on a user. Heavy related collections
    are summarised by counts so the export stays a single deliverable."""
    from models.portal.request import MediaRequest
    from models.portal.ticket import Ticket
    from models.portal.social import UserList, UserRating
    from models.portal.achievement import UserAchievement
    from models.portal.chat import ChatMessage

    async def _count(model, attr: str = "user_id") -> int:
        col = getattr(model, attr)
        return (await db.execute(select(func.count()).where(col == user.id))).scalar() or 0

    counts = {
        "requests": await _count(MediaRequest),
        "tickets": await _count(Ticket),
        "lists": await _count(UserList),
        "ratings": await _count(UserRating),
        "achievements": await _count(UserAchievement),
        "chat_messages": await _count(ChatMessage),
    }

    def _iso(d):
        return d.isoformat() if d else None
    payload = {
        "exported_at": now_utc().isoformat(),
        "user": {
            "id": user.id, "username": user.username,
            "is_active": user.is_active, "created_at": _iso(user.created_at),
        },
        "profile": {
            "id": profile.id, "display_name": profile.display_name,
            "first_name": profile.first_name, "last_name": profile.last_name,
            "email": profile.email, "source": profile.source,
            "emby_user_id": profile.emby_user_id, "role": profile.role,
            "level": profile.level, "xp": profile.xp,
            "language": profile.language, "is_public": profile.is_public,
            "tags": profile.tags or [],
            "permissions": {key: bool(getattr(profile, key)) for key in PERMISSION_KEYS},
            "access_start_date": _iso(profile.access_start_date),
            "access_end_date": _iso(profile.access_end_date),
            "last_login_at": _iso(profile.last_login_at),
            "last_login_ip": profile.last_login_ip,
            "last_login_user_agent": profile.last_login_user_agent,
            "bio": profile.bio,
        },
        "counts": counts,
    }
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=user.id,
        action=ACTION_USER_RGPD_EXPORT,
        ip=ip,
        user_agent=user_agent,
    )
    return payload


async def run_bulk_action(
    db: AsyncSession,
    *,
    profile_ids: Iterable[int],
    action: str,
    payload: dict[str, Any] | None,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if action not in BULK_ACTIONS:
        return {"error": "invalid_action"}
    ids = [int(pid) for pid in profile_ids if pid]
    if not ids:
        return {"error": "no_target"}

    rows = (await db.execute(
        select(UserProfile, User)
        .join(User, User.id == UserProfile.user_id)
        .where(UserProfile.id.in_(ids))
    )).all()

    processed = 0
    skipped: list[dict[str, Any]] = []
    for profile, user in rows:
        # Always exclude the admin themselves from a bulk mutation that
        # would lock them out — never trust the front-end checkbox state.
        if admin_user_id is not None and admin_user_id == user.id and action in (
            BULK_DEACTIVATE, BULK_DELETE,
        ):
            skipped.append({"id": profile.id, "reason": "self_action_forbidden"})
            continue
        result: dict[str, Any] | None = None
        if action == BULK_ACTIVATE:
            result = await set_account_active(
                db, profile, user, active=True, admin_user_id=admin_user_id,
                ip=ip, user_agent=user_agent,
            )
        elif action == BULK_DEACTIVATE:
            result = await set_account_active(
                db, profile, user, active=False, admin_user_id=admin_user_id,
                ip=ip, user_agent=user_agent,
            )
        elif action == BULK_DELETE:
            result = await soft_delete_user(
                db, profile, user, admin_user_id=admin_user_id,
                ip=ip, user_agent=user_agent,
            )
        elif action == BULK_SET_ROLE:
            new_role = (payload or {}).get("role")
            if new_role in ROLES:
                result = await update_role(
                    db, profile, role=new_role, admin_user_id=admin_user_id,
                    ip=ip, user_agent=user_agent,
                )
            else:
                result = {"error": "invalid_role"}
        elif action == BULK_SET_PERMISSIONS:
            perms = (payload or {}).get("permissions") or {}
            scoped = {k: bool(v) for k, v in perms.items() if k in PERMISSION_KEYS}
            if scoped:
                result = await update_permissions(
                    db, profile, permissions=scoped, admin_user_id=admin_user_id,
                    ip=ip, user_agent=user_agent,
                )
            else:
                result = {"error": "no_permissions"}
        if result is None or (isinstance(result, dict) and result.get("error")):
            reason = (result or {}).get("error", "no_op")
            skipped.append({"id": profile.id, "reason": reason})
        else:
            processed += 1

    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=None,
        action=ACTION_USER_BULK,
        payload={"action": action, "count": processed, "ids": ids, "extra": payload},
        ip=ip,
        user_agent=user_agent,
    )
    return {"ok": True, "processed": processed, "skipped": skipped}
