"""Shared fixtures + factory helpers for the premium settings test suite.

Loaded by ``test_portal_username_lock.py`` and ``test_portal_avatar_upload.py``.
Kept out of ``conftest.py`` because the helpers are scoped to one feature.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from core.security import create_access_token, hash_password
from models.portal.profile import UserProfile
from models.user import User


PORTAL_COOKIE = "rq_token"

# Sentinel that distinguishes "argument omitted" from "explicit None". Tests
# that need a local-only profile (no Emby account) pass ``emby_user_id=None``
# on purpose; everything else falls back to a unique auto-generated value.
_EMBY_USER_ID_UNSET: Any = object()


def portal_token(username: str) -> str:
    return create_access_token({"sub": username, "scope": "portal"})


async def make_portal_user(
    db_session,
    *,
    username: str,
    display_name: str | None = None,
    role: str = "viewer",
    is_public: bool = True,
    must_set: bool = False,
    changed_days_ago: int | None = None,
    emby_user_id: str | None = _EMBY_USER_ID_UNSET,
) -> tuple[User, UserProfile]:
    user = User(
        username=username,
        hashed_password=hash_password("dummy"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    changed_at = None
    if changed_days_ago is not None:
        changed_at = datetime.now(timezone.utc) - timedelta(days=changed_days_ago)

    # Ranking surfaces (compute_ranking, leaderboard widgets) exclude any
    # profile whose ``emby_user_id`` is NULL, treating it as a non-Emby
    # local-only account. Default to a unique auto-generated value so the
    # user shows up in ranking assertions; tests that intentionally want
    # a local-only profile pass ``emby_user_id=None`` explicitly.
    resolved_emby_user_id = (
        f"emby-{username}"
        if emby_user_id is _EMBY_USER_ID_UNSET
        else emby_user_id
    )

    profile = UserProfile(
        user_id=user.id,
        display_name=display_name or username,
        role=role,
        account_active=True,
        is_public=is_public,
        display_name_must_set=must_set,
        display_name_changed_at=changed_at,
        emby_user_id=resolved_emby_user_id,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile
