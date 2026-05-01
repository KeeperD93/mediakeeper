"""Tests for /api/portal/admin/requests/*."""

import pytest

from core.security import create_access_token
from models.portal.profile import UserProfile


@pytest.mark.asyncio
async def test_list_users_returns_profiles(client, admin_user, db_session):
    """La liste admin des users doit renvoyer les profils Demandes."""
    profile = UserProfile(
        user_id=admin_user.id,
        display_name="Admin User",
        role="admin",
        account_active=True,
        chat_enabled=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username}))
    resp = await client.get("/api/portal/admin/requests/users")

    assert resp.status_code == 200
    assert resp.json()["items"] == [
        {
            "id": profile.id,
            "user_id": admin_user.id,
            "username": "admin",
            "display_name": "Admin User",
            "avatar_url": None,
            "role": "admin",
            "account_active": True,
            "chat_enabled": True,
            "is_public": True,
            "forced_public": None,
            "level": 1,
            "xp": 0,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
        }
    ]
