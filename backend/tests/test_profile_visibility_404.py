"""``GET /api/portal/profiles/by-user-id/{user_id}/public`` visibility
contract for the public profile endpoint.

Three cases coexist:

* Missing profile (or admin viewed by a non-admin) → 404. These IDs
  are never exposed by any other public surface, so masking them as
  "not found" prevents enumeration.
* Private profile viewed by a non-owner → 200 with a minimal
  ``{is_private, user_id, display_name, avatar_url}`` placeholder.
  The leaderboard already exposes ``user_id`` for every ranked
  player (both public and private), so 404-masking here would
  break the UX without gaining any privacy.
* Public profile → 200 with the full payload.
"""
from __future__ import annotations

import pytest

from core.security import hash_password
from models.user import User
from models.portal.profile import UserProfile


async def _make_user(db_session, *, username: str, is_public: bool):
    user = User(
        username=username,
        hashed_password=hash_password("AnyPassword123!"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        is_public=is_public,
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


@pytest.mark.asyncio
async def test_private_profile_returns_placeholder(client, admin_user, db_session, portal_login):
    """Private profile reached by a non-owner → 200 + placeholder."""
    await portal_login(client)
    user, _ = await _make_user(db_session, username="private", is_public=False)
    r = await client.get(f"/api/portal/profiles/by-user-id/{user.id}/public")
    assert r.status_code == 200
    body = r.json()
    assert body["is_private"] is True
    assert body["user_id"] == user.id
    assert "display_name" in body
    # Sensitive fields stay out of the placeholder.
    assert "bio" not in body
    assert "ranking" not in body


@pytest.mark.asyncio
async def test_missing_profile_returns_404(client, admin_user, db_session, portal_login):
    """Missing IDs stay opaque — same 404 shape regardless of cause."""
    await portal_login(client)
    r = await client.get("/api/portal/profiles/by-user-id/99999/public")
    assert r.status_code == 404
    assert r.json()["detail"] == "profile_not_found"


@pytest.mark.asyncio
async def test_public_profile_still_returns_200(client, admin_user, db_session, portal_login):
    await portal_login(client)
    user, _ = await _make_user(db_session, username="public", is_public=True)
    r = await client.get(f"/api/portal/profiles/by-user-id/{user.id}/public")
    assert r.status_code == 200
