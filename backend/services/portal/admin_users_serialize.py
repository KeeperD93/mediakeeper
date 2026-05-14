"""Serialisers + helpers shared by every admin_users_* module.

Kept in its own file so neither the list/CRUD module nor the action
modules drift over the 300-line cap when they grow new fields.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models.user import User
from models.portal.profile import UserProfile
from services.portal._display_name import resolve_display_name

from .admin_users_constants import (
    ONLINE_WINDOW_SECONDS,
    PERMISSION_KEYS,
    SOURCE_EMBY,
    SOURCE_LOCAL,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _aware(value: datetime | None) -> datetime | None:
    """SQLite (test env) sometimes hands back tz-naive datetimes — pin
    them to UTC so the comparisons below never raise."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def is_online(profile: UserProfile, *, ref: datetime | None = None) -> bool:
    seen = _aware(profile.last_seen_at)
    if not seen:
        return False
    ref = ref or now_utc()
    return (ref - seen).total_seconds() < ONLINE_WINDOW_SECONDS


def expires_in_days(profile: UserProfile, *, ref: datetime | None = None) -> int | None:
    end = _aware(profile.access_end_date)
    if not end:
        return None
    ref = ref or now_utc()
    return (end - ref).days


def is_expired(profile: UserProfile, *, ref: datetime | None = None) -> bool:
    end = _aware(profile.access_end_date)
    if not end:
        return False
    ref = ref or now_utc()
    return end <= ref


def serialize_admin_user_row(profile: UserProfile, user: User) -> dict[str, Any]:
    """Compact payload used by the list view (no heavy detail fields).

    ``display_name`` falls back to the same stable ``Utilisateur 1234``
    alias the user-facing surfaces (leaderboard, chat, lists) show when
    the operator hasn't picked their own portal pseudo yet — keeps the
    same identity across every admin and user view. The Emby
    ``username`` stays available in the dedicated field for operators
    who need the raw identifier."""
    ref = now_utc()
    return {
        "id": profile.id,
        "user_id": user.id,
        "username": user.username,
        "display_name": resolve_display_name(profile.display_name, user.id),
        "avatar_url": profile.avatar_url,
        "avatar_custom_path": profile.avatar_custom_path,
        "email": profile.email,
        "source": profile.source or (SOURCE_EMBY if profile.emby_user_id else SOURCE_LOCAL),
        "role": profile.role,
        "account_active": bool(profile.account_active and user.is_active),
        "emby_is_disabled": profile.emby_is_disabled,
        "level": profile.level,
        "xp": profile.xp,
        "tags": profile.tags or [],
        "permissions": {key: bool(getattr(profile, key)) for key in PERMISSION_KEYS},
        "access_start_date": iso(profile.access_start_date),
        "access_end_date": iso(profile.access_end_date),
        "expires_in_days": expires_in_days(profile, ref=ref),
        "is_expired": is_expired(profile, ref=ref),
        "last_seen_at": iso(profile.last_seen_at),
        "last_login_at": iso(profile.last_login_at),
        "online": is_online(profile, ref=ref),
        "deleted_at": iso(profile.deleted_at),
        # GDPR opt-in (Batch 11B): timestamps live on ``users``, not
        # ``user_profiles``. Surfaced here so the admin list can power
        # the "Pending deletion" DataTable + Cancel button.
        "deletion_requested_at": iso(getattr(user, "deletion_requested_at", None)),
        "pending_deletion_at": iso(getattr(user, "pending_deletion_at", None)),
        "created_at": iso(profile.created_at),
        "updated_at": iso(profile.updated_at),
    }


def serialize_admin_user_detail(profile: UserProfile, user: User) -> dict[str, Any]:
    """Full payload used by the drawer header + identity tab."""
    base = serialize_admin_user_row(profile, user)
    base.update({
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "bio": profile.bio,
        "emby_user_id": profile.emby_user_id,
        "language": profile.language,
        "is_public": profile.is_public,
        "hide_adult": profile.hide_adult,
        "chat_enabled": profile.chat_enabled,
        "chat_muted_until": iso(profile.chat_muted_until),
        "last_login_ip": profile.last_login_ip,
        "last_login_user_agent": profile.last_login_user_agent,
        "admin_notes": profile.admin_notes,
        "display_name_must_set": profile.display_name_must_set,
        "display_name_changed_at": iso(profile.display_name_changed_at),
        "tokens_invalidated_at": iso(profile.tokens_invalidated_at),
    })
    return base
