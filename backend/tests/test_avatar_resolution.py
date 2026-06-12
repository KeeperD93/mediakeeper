"""Custom uploaded avatars must win over the Emby-proxied URL everywhere.

``resolve_avatar_url`` is the single source of truth for that precedence;
every serializer that exposes an avatar routes through it. Each integration
test also pins the neighbouring ``level`` field so an off-by-one in the row
unpacking (the column was inserted mid-SELECT on several sites) is caught.
"""
from unittest.mock import AsyncMock, patch

import pytest

from core.security import create_access_token
from models.portal.profile import UserProfile
from models.portal.social import PRIVACY_COLLABORATIVE, UserList, UserListContributor
from models.user import User
from services.emby.sessions import get_sessions
from services.portal.avatars import resolve_avatar_url
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

EMBY_URL = "https://emby.example/ignored.png"


# ── helper unit ──────────────────────────────────────────────────────────

def test_resolve_avatar_url_custom_path_wins():
    assert (
        resolve_avatar_url(EMBY_URL, "17_123.png") == "/api/portal/avatars/17_123.png"
    )


def test_resolve_avatar_url_falls_back_to_emby_url():
    assert resolve_avatar_url("/api/emby/user-image/X", None) == "/api/emby/user-image/X"


def test_resolve_avatar_url_none_when_empty():
    assert resolve_avatar_url(None, None) is None


# ── admin surfaces ───────────────────────────────────────────────────────

def _admin_auth(client, admin_user):
    client.cookies.set(
        "mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"})
    )


@pytest.mark.asyncio
async def test_auth_me_resolves_custom_avatar(client, admin_user, db_session):
    """Admin topbar + logout popup source (/api/auth/me)."""
    db_session.add(UserProfile(
        user_id=admin_user.id, display_name="Admin", role="admin",
        account_active=True, level=7,
        avatar_url=EMBY_URL, avatar_custom_path="admin_42.png",
    ))
    await db_session.commit()
    _admin_auth(client, admin_user)
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["avatar_url"] == "/api/portal/avatars/admin_42.png"
    assert body["level"] == 7  # named row access must not scramble the level


@pytest.mark.asyncio
async def test_admin_users_list_resolves_custom_avatar(client, admin_user, db_session):
    """Premium admin user management (admin/portal/users)."""
    db_session.add(UserProfile(
        user_id=admin_user.id, display_name="Admin", role="admin",
        source="local", account_active=True,
        avatar_url=EMBY_URL, avatar_custom_path="admin_99.png",
    ))
    await db_session.commit()
    _admin_auth(client, admin_user)
    resp = await client.get("/api/portal/admin/users?source=local")
    assert resp.status_code == 200
    row = resp.json()["items"][0]
    assert row["avatar_url"] == "/api/portal/avatars/admin_99.png"
    assert row["avatar_custom_path"] == "admin_99.png"


@pytest.mark.asyncio
async def test_get_sessions_resolves_custom_avatar(db_session):
    """Admin dashboard active-sessions hero strip."""
    user = User(
        username="streamer", hashed_password="x", is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    db_session.add(UserProfile(
        user_id=user.id, display_name="streamer", role="viewer",
        account_active=True, emby_user_id="EMBY-S", level=5,
        avatar_url=EMBY_URL, avatar_custom_path="s_1.png",
    ))
    await db_session.commit()

    raw = [{"UserName": "streamer", "UserId": "EMBY-S", "NowPlayingItem": None, "PlayState": {}}]
    with patch(
        "services.emby.sessions.get_raw_sessions", new=AsyncMock(return_value=raw)
    ):
        result = await get_sessions(db_session)

    assert len(result) == 1
    assert result[0]["avatar_url"] == "/api/portal/avatars/s_1.png"
    assert result[0]["level"] == 5


# ── portal surfaces ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_contributors_resolve_custom_avatar(client, db_session):
    """Collaborative-list contributors panel."""
    owner, _ = await make_portal_user(db_session, username="av-owner")
    contributor, contrib_profile = await make_portal_user(db_session, username="av-contributor")
    contrib_profile.avatar_url = EMBY_URL
    contrib_profile.avatar_custom_path = "contrib_3.png"
    lst = UserList(user_id=owner.id, name="Collab", privacy=PRIVACY_COLLABORATIVE)
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)
    db_session.add(UserListContributor(list_id=lst.id, user_id=contributor.id))
    await db_session.commit()

    client.cookies.set(PORTAL_COOKIE, portal_token(owner.username))
    resp = await client.get(f"/api/portal/lists/{lst.id}")
    assert resp.status_code == 200
    contributors = resp.json().get("contributors") or []
    row = next(c for c in contributors if c["user_id"] == contributor.id)
    assert row["avatar_url"] == "/api/portal/avatars/contrib_3.png"
    assert row["level"] == 1  # level still reads correctly after the unpack change


@pytest.mark.asyncio
async def test_search_users_resolves_custom_avatar(client, db_session):
    """Portal user-search picker (event invite)."""
    me, _ = await make_portal_user(db_session, username="av-searcher")
    target, target_profile = await make_portal_user(
        db_session, username="findme", display_name="FindMe",
    )
    target_profile.avatar_url = EMBY_URL
    target_profile.avatar_custom_path = "find_8.png"
    target_profile.level = 9
    await db_session.commit()

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/profiles/search/users?q=FindMe")
    assert resp.status_code == 200
    row = next(i for i in resp.json()["items"] if i["id"] == target.id)
    assert row["avatar_url"] == "/api/portal/avatars/find_8.png"
    assert row["level"] == 9  # r[6] after inserting the avatar_custom_path column
