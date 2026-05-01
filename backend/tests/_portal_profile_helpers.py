"""Shared fixtures + factory helpers for the premium settings test suite.

Loaded by ``test_portal_username_lock.py`` and ``test_portal_avatar_upload.py``.
Kept out of ``conftest.py`` because the helpers are scoped to one feature.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.security import create_access_token, hash_password
from models.portal.profile import UserProfile
from models.user import User


PORTAL_COOKIE = "rq_token"


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

    profile = UserProfile(
        user_id=user.id,
        display_name=display_name or username,
        role=role,
        account_active=True,
        is_public=is_public,
        display_name_must_set=must_set,
        display_name_changed_at=changed_at,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile
