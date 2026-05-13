"""Portal profile serialization helpers."""
from datetime import datetime, timedelta, timezone

from core.security import has_backoffice_access
from models.portal.profile import UserProfile
from models.user import User
from services.portal._display_name import resolve_display_name
from services.portal.avatars import avatar_public_url

DISPLAY_NAME_LOCK_DAYS = 30 * 6  # 6 months


def display_name_locked_until(profile: UserProfile) -> datetime | None:
    """Return the unlock datetime, or None if the name is currently free to change."""
    if profile.display_name_must_set:
        return None
    changed_at = profile.display_name_changed_at
    if not changed_at:
        return None
    if changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=timezone.utc)
    return changed_at + timedelta(days=DISPLAY_NAME_LOCK_DAYS)


def serialize_profile(profile: UserProfile, *, user: User | None = None) -> dict:
    """Full profile serialization (for the owner).

    Pass ``user`` for the per-user "me" endpoints so the payload exposes
    ``has_backoffice_access`` — admin list views skip it (defaults False)."""
    title_tier = None
    if profile.selected_title:
        from services.portal.achievement_defs import ACHIEVEMENT_DEFS, TITLE_REWARDS
        for ach_id, title_key in TITLE_REWARDS.items():
            if title_key == profile.selected_title:
                ach_def = next((d for d in ACHIEVEMENT_DEFS if d["id"] == ach_id), None)
                if ach_def:
                    title_tier = ach_def.get("tier", 1)
                break
    locked_until = display_name_locked_until(profile)
    must_set = bool(profile.display_name_must_set) and profile.role != "admin"
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "display_name": profile.display_name,
        "display_name_must_set": must_set,
        "display_name_changed_at": profile.display_name_changed_at.isoformat()
            if profile.display_name_changed_at else None,
        "display_name_locked_until": locked_until.isoformat() if locked_until else None,
        "avatar_url": _resolve_avatar_url(profile),
        "avatar_emby_url": profile.avatar_url,
        "avatar_is_custom": bool(profile.avatar_custom_path),
        "bio": profile.bio,
        "favorite_genres": profile.favorite_genres,
        "level": profile.level,
        "xp": profile.xp,
        "selected_badges": profile.selected_badges,
        "selected_title": profile.selected_title,
        "title_tier": title_tier,
        "avatar_effect": profile.avatar_effect,
        "is_public": profile.is_public,
        "forced_public": profile.forced_public,
        "role": profile.role,
        "language": profile.language,
        "chat_enabled": profile.chat_enabled,
        "account_active": profile.account_active,
        "hide_adult": profile.hide_adult,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "access_end_date": profile.access_end_date.isoformat() if profile.access_end_date else None,
        "has_backoffice_access": has_backoffice_access(
            user.username if user else None,
            user.hashed_password if user else None,
            is_active=bool(user.is_active) if user else False,
        ),
    }


def serialize_public_profile(profile: UserProfile, *, lang: str = "fr") -> dict:
    """Public profile (limited info).

    Privacy boundary (Rules §22): when the owner has not picked a portal
    pseudo yet, render the localized anonymous alias instead of the
    auto-populated Emby username so other viewers can never derive it.
    """
    effective = None if profile.display_name_must_set else profile.display_name
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "display_name": resolve_display_name(effective, profile.user_id, lang),
        "avatar_url": _resolve_avatar_url(profile),
        "bio": profile.bio,
        "level": profile.level,
        "xp": profile.xp,
        "selected_badges": profile.selected_badges,
        "selected_title": profile.selected_title,
        "avatar_effect": profile.avatar_effect,
        "favorite_genres": profile.favorite_genres,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "is_public": bool(profile.is_public),
    }


def _resolve_avatar_url(profile: UserProfile) -> str | None:
    """A custom uploaded avatar takes precedence over the Emby-proxied URL."""
    if profile.avatar_custom_path:
        return avatar_public_url(profile.avatar_custom_path)
    return profile.avatar_url


def build_private_placeholder(profile: UserProfile, *, lang: str) -> dict:
    """Minimal payload returned when a non-owner reaches a private profile.

    The leaderboard exposes ``user_id`` for every ranked player (public
    *and* private accounts), so the dedicated /portal/leaderboard page
    can — and will — link to a private profile. Surfacing a polite
    "this profile is private" landing keeps the click meaningful;
    masking it as 404 would only confuse the user without gaining any
    privacy (the id is already known).

    The payload deliberately carries only the safe identity bits
    (anonymised display name + avatar) plus ``is_private=True`` so the
    SPA can branch on it.
    """
    effective_name = None if profile.display_name_must_set else profile.display_name
    return {
        "is_private": True,
        "user_id": profile.user_id,
        "display_name": resolve_display_name(effective_name, profile.user_id, lang),
        "avatar_url": _resolve_avatar_url(profile),
    }
