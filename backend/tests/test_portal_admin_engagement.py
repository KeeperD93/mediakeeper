"""Tests for GET /api/portal/admin/engagement."""
from datetime import datetime, timedelta, timezone

import pytest

from core.security import create_access_token
from models.portal.profile import UserProfile
from models.portal.social import UserList


def _utc_now():
    return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_engagement_requires_admin(client):
    resp = await client.get("/api/portal/admin/engagement")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_engagement_counts_lists_within_window(client, admin_user, db_session):
    profile = UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()

    recent = UserList(user_id=admin_user.id, name="Recent", created_at=_utc_now())
    old = UserList(user_id=admin_user.id, name="Old",
                   created_at=_utc_now() - timedelta(days=10))
    deleted = UserList(user_id=admin_user.id, name="Deleted",
                       created_at=_utc_now(), is_deleted=True)
    db_session.add_all([recent, old, deleted])
    await db_session.commit()

    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username}))

    # 24h window: only "recent" counts (deleted excluded, old outside window)
    resp = await client.get("/api/portal/admin/engagement?window=1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["window_days"] == 1
    assert body["new_lists"] == 1
    assert body["achievements_unlocked"] == 0
    assert body["chat_messages"] == 0
    assert body["reviews"] == 0

    # 7d window: still only "recent" (old list 10d ago is still outside)
    resp = await client.get("/api/portal/admin/engagement?window=7")
    assert resp.status_code == 200
    assert resp.json()["new_lists"] == 1


@pytest.mark.asyncio
async def test_engagement_invalid_window_falls_back_to_24h(client, admin_user, db_session):
    profile = UserProfile(user_id=admin_user.id, display_name="Admin", role="admin")
    db_session.add(profile)
    await db_session.commit()

    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username}))
    resp = await client.get("/api/portal/admin/engagement?window=99")
    assert resp.status_code == 200
    assert resp.json()["window_days"] == 1
