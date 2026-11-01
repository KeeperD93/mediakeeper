"""Snapshot helper for the GDPR opt-in export.

Lives in its own private module so ``gdpr.py`` stays under the 300-
line cap. The public entry point remains ``services.portal.gdpr.
_collect_full_user_data`` (re-exported there) — call sites and tests
do not import from this module directly.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement, UserAchievement
from models.portal.chat import ChatMessage
from models.portal.event import WatchPartyParticipant
from models.portal.login_history import UserLoginHistory
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.portal.social import (
    ReleaseReminder,
    UserList,
    UserListItem,
    UserRating,
)
from models.security import SecurityAttempt
from models.user import User
from models.user_preferences import UserPreference


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _profile_to_dict(profile: UserProfile) -> dict[str, Any]:
    """Serialise a profile for the export.

    ``admin_notes`` and ``tags`` are stripped on purpose: they are admin
    curation artefacts, not user-generated content, and the user has no
    expectation to see them in their own GDPR export. ``deleted_at`` and
    ``deleted_by_user_id`` are left out too: a deleted account cannot sign
    in to ask for an export, so they would always be empty.
    """
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "display_name": profile.display_name,
        "display_name_must_set": profile.display_name_must_set,
        "display_name_changed_at": _iso(profile.display_name_changed_at),
        "avatar_url": profile.avatar_url,
        "avatar_custom_path": profile.avatar_custom_path,
        "bio": profile.bio,
        "favorite_genres": profile.favorite_genres,
        "level": profile.level,
        "xp": profile.xp,
        "selected_badges": profile.selected_badges,
        "selected_title": profile.selected_title,
        "avatar_effect": profile.avatar_effect,
        "is_public": profile.is_public,
        "role": profile.role,
        "language": profile.language,
        "chat_enabled": profile.chat_enabled,
        "chat_muted_until": _iso(profile.chat_muted_until),
        "chat_last_read_message_id": profile.chat_last_read_message_id,
        "hide_adult": profile.hide_adult,
        "account_active": profile.account_active,
        "forced_public": profile.forced_public,
        "source": profile.source,
        "emby_user_id": profile.emby_user_id,
        "emby_is_disabled": profile.emby_is_disabled,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "email": profile.email,
        "access_start_date": _iso(profile.access_start_date),
        "access_end_date": _iso(profile.access_end_date),
        "last_seen_at": _iso(profile.last_seen_at),
        "last_login_at": _iso(profile.last_login_at),
        "last_login_ip": profile.last_login_ip,
        "last_login_user_agent": profile.last_login_user_agent,
        "can_chat": profile.can_chat,
        "can_portal": profile.can_portal,
        "can_problems": profile.can_problems,
        "can_lists": profile.can_lists,
        "can_earn_xp_offline": profile.can_earn_xp_offline,
        "can_report_feedback": profile.can_report_feedback,
        "tokens_invalidated_at": _iso(profile.tokens_invalidated_at),
        "created_at": _iso(profile.created_at),
        "updated_at": _iso(profile.updated_at),
    }


async def collect_full_user_data(
    db: AsyncSession, user: User, profile: UserProfile,
) -> dict[str, Any]:
    """Snapshot the user's rows in the tables in scope. The archive's README
    says what is excluded on purpose and what is not exported yet."""
    uid = user.id
    out: dict[str, Any] = {
        "metadata": {
            "schema_version": 1,
            "user_id": uid,
            "username": user.username,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        },
        "user_profile": _profile_to_dict(profile),
    }

    pref = (await db.execute(
        select(UserPreference).where(UserPreference.user_id == uid)
    )).scalar_one_or_none()
    out["user_preferences"] = (
        {
            "preferences": pref.preferences,
            "dashboard_layout": pref.dashboard_layout,
            "updated_at": _iso(pref.updated_at),
        }
        if pref else None
    )

    lists = (await db.execute(
        select(UserList).where(UserList.user_id == uid)
    )).scalars().all()
    list_ids = [lst.id for lst in lists]
    out["user_lists"] = [
        {
            "id": lst.id,
            "name": lst.name,
            "description": lst.description,
            "privacy": lst.privacy,
            "content_type": lst.content_type,
            "genres": lst.genres,
            "sort_order": lst.sort_order,
            "copy_count": lst.copy_count,
            "is_deleted": bool(lst.is_deleted),
            "created_at": _iso(lst.created_at),
            "updated_at": _iso(lst.updated_at),
        }
        for lst in lists
    ]

    items: list[UserListItem] = []
    if list_ids:
        items.extend((await db.execute(
            select(UserListItem).where(UserListItem.list_id.in_(list_ids))
        )).scalars().all())
    contrib_items = (await db.execute(
        select(UserListItem).where(UserListItem.added_by_user_id == uid)
    )).scalars().all()
    seen_ids = {i.id for i in items}
    for item in contrib_items:
        if item.id not in seen_ids:
            items.append(item)
    out["user_list_items"] = [
        {
            "id": item.id,
            "list_id": item.list_id,
            "tmdb_id": item.tmdb_id,
            "media_type": item.media_type,
            "title": item.title,
            "year": item.year,
            "added_by_user_id": item.added_by_user_id,
            "added_at": _iso(item.added_at),
        }
        for item in items
    ]

    ratings = (await db.execute(
        select(UserRating).where(UserRating.user_id == uid)
    )).scalars().all()
    out["user_ratings"] = [
        {
            "id": r.id,
            "tmdb_id": r.tmdb_id,
            "media_type": r.media_type,
            "rating": r.rating,
            "review": r.review,
            "created_at": _iso(r.created_at),
        }
        for r in ratings
    ]

    rows = (await db.execute(
        select(UserAchievement, Achievement)
        .join(Achievement, Achievement.id == UserAchievement.achievement_id)
        .where(UserAchievement.user_id == uid)
    )).all()
    out["user_achievements"] = [
        {
            "achievement_id": ua.achievement_id,
            "category": ach.category,
            "tier": ach.tier,
            "progress": ua.progress,
            "unlocked": bool(ua.unlocked),
            "unlocked_at": _iso(ua.unlocked_at),
        }
        for ua, ach in rows
    ]

    reminders = (await db.execute(
        select(ReleaseReminder).where(ReleaseReminder.user_id == uid)
    )).scalars().all()
    out["release_reminders"] = [
        {
            "id": r.id,
            "tmdb_id": r.tmdb_id,
            "media_type": r.media_type,
            "release_date": _iso(r.release_date),
            "notified": bool(r.notified),
        }
        for r in reminders
    ]

    msgs = (await db.execute(
        select(ChatMessage).where(ChatMessage.user_id == uid)
    )).scalars().all()
    out["chat_messages"] = [
        {
            "id": m.id,
            "room_id": m.room_id,
            "content": m.content,
            "deleted": bool(m.deleted),
            "created_at": _iso(m.created_at),
        }
        for m in msgs
    ]

    requests = (await db.execute(
        select(MediaRequest).where(MediaRequest.user_id == uid)
    )).scalars().all()
    out["media_requests"] = [
        {
            "id": r.id,
            "tmdb_id": r.tmdb_id,
            "media_type": r.media_type,
            "title": r.title,
            "year": r.year,
            "status": r.status,
            "reject_reason": r.reject_reason,
            "auto_approved": bool(r.auto_approved),
            "requested_seasons": r.requested_seasons,
            "created_at": _iso(r.created_at),
            "updated_at": _iso(r.updated_at),
        }
        for r in requests
    ]

    participations = (await db.execute(
        select(WatchPartyParticipant).where(WatchPartyParticipant.user_id == uid)
    )).scalars().all()
    out["watch_party_participants"] = [
        {
            "id": p.id,
            "party_id": p.party_id,
            "joined_at": _iso(p.joined_at),
        }
        for p in participations
    ]

    history = (await db.execute(
        select(UserLoginHistory).where(UserLoginHistory.user_id == uid)
    )).scalars().all()
    out["user_login_history"] = [
        {
            "id": h.id,
            "source": h.source,
            "success": bool(h.success),
            "ip": h.ip,
            "user_agent": h.user_agent,
            "created_at": _iso(h.created_at),
        }
        for h in history
    ]

    # The log holds the name typed, not an account id: lower-cased in Python, which the
    # database may not match on accented capitals, or as typed in older rows. Older than
    # the account, a row is a past holder's. A failure may carry a stranger's address.
    sign_ins = (await db.execute(
        select(SecurityAttempt).where(
            or_(
                SecurityAttempt.username == user.username.lower(),
                func.lower(SecurityAttempt.username) == func.lower(user.username),
            ),
            SecurityAttempt.success == 1,
            SecurityAttempt.created_at >= user.created_at,
        ).order_by(SecurityAttempt.id)
    )).scalars().all()
    out["security_attempts"] = [
        {
            "id": a.id,
            "scope": a.scope,
            "ip": a.ip,
            "user_agent": a.user_agent,
            "created_at": _iso(a.created_at),
        }
        for a in sign_ins
    ]

    return out
