"""Regression guards around the visibility of disabled and soft-deleted
accounts across the portal surfaces.

Five concerns are covered:

* ``soft_delete_user`` and ``set_account_active(active=False)`` stamp
  ``tokens_invalidated_at`` on both the ``users`` and ``user_profiles``
  rows so a pre-issued JWT cannot be replayed even if a downstream
  check were to slip the ``is_active`` / ``account_active`` gate.
  ``restore_user`` and a follow-up re-activation deliberately leave
  the pivot in place — a fresh login mints a newer ``iat`` that beats
  the stamp on its own.
* The user picker (``GET /api/portal/profiles/search/users``) excludes
  soft-deleted and de-activated profiles on top of the pre-existing
  ``User.is_active`` filter.
* ``get_public_lists`` hides lists owned by a soft-deleted or
  de-activated user so ``owner_username`` cannot leak.
* ``get_media_ratings`` hides reviews authored by a soft-deleted or
  de-activated user.
* ``get_contributors`` hides contributors who are soft-deleted or
  de-activated from the collaborative-list panel.

These guards are defence-in-depth on top of the existing auth
dependencies — together they prevent a stale pseudo, avatar or
review from surfacing once the account has been disabled.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.security import create_access_token, hash_password
from models.portal.profile import UserProfile
from models.portal.social import (
    PRIVACY_COLLABORATIVE,
    PRIVACY_PUBLIC_READONLY,
    UserList,
    UserListContributor,
    UserRating,
)
from models.user import User
from services.portal.admin_users_actions import set_account_active
from services.portal.admin_users_lifecycle import restore_user, soft_delete_user
from services.portal.lists_admin import get_contributors
from services.portal.lists_query import get_public_lists
from services.portal.social import get_media_ratings


# ─────────────────────────── helpers ───────────────────────────


async def _make_user_with_profile(
    db_session,
    *,
    username: str,
    role: str = "viewer",
    account_active: bool = True,
    deleted_at: datetime | None = None,
    is_active: bool = True,
) -> tuple[User, UserProfile]:
    user = User(
        username=username,
        hashed_password=hash_password("dummy"),
        is_active=is_active,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role=role,
        account_active=account_active,
        deleted_at=deleted_at,
        # These fixtures model accounts that have completed their first-time
        # onboarding (pseudo picked), so user-facing endpoints return the
        # ``display_name`` verbatim rather than the anonymous alias.
        display_name_must_set=False,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


def _set_portal_cookie(client, user: User) -> None:
    client.cookies.set(
        "rq_token",
        create_access_token({"sub": user.username, "scope": "portal"}),
    )


# ═══════════════════════════════════════════════════════════════════
# token revocation on account disable
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_soft_delete_user_stamps_tokens_invalidated_at_on_both_scopes(db_session):
    """Soft-delete must revoke pre-existing JWTs on admin (``users``)
    AND portal (``user_profiles``) scope simultaneously."""
    user, profile = await _make_user_with_profile(db_session, username="sd-target")
    assert user.tokens_invalidated_at is None
    assert profile.tokens_invalidated_at is None

    result = await soft_delete_user(
        db_session, profile, user, admin_user_id=999,
    )
    assert result == {"ok": True}

    await db_session.refresh(user)
    await db_session.refresh(profile)
    assert user.is_active is False
    assert profile.deleted_at is not None
    assert profile.account_active is False
    # Belt-and-braces: both scopes carry the revocation pivot.
    assert user.tokens_invalidated_at is not None
    assert profile.tokens_invalidated_at is not None
    # Both stamps were written in the same call → equal timestamps.
    assert user.tokens_invalidated_at == profile.tokens_invalidated_at


@pytest.mark.asyncio
async def test_set_account_active_false_stamps_tokens_invalidated_at(db_session):
    """An admin de-activation must revoke active JWTs the same way
    soft-delete does."""
    user, profile = await _make_user_with_profile(db_session, username="deact-target")
    assert user.tokens_invalidated_at is None
    assert profile.tokens_invalidated_at is None

    result = await set_account_active(
        db_session, profile, user, active=False, admin_user_id=999,
    )
    assert result == {"ok": True}

    await db_session.refresh(user)
    await db_session.refresh(profile)
    assert user.is_active is False
    assert profile.account_active is False
    assert user.tokens_invalidated_at is not None
    assert profile.tokens_invalidated_at is not None


@pytest.mark.asyncio
async def test_restore_does_not_clear_revocation_pivots(db_session):
    """Restore puts ``account_active`` back to True but the
    ``tokens_invalidated_at`` pivots stay in place. A user re-logging
    in mints a fresh JWT whose ``iat`` is newer than the stamp, so the
    auth deps accept it. Old JWTs stay revoked — desired."""
    user, profile = await _make_user_with_profile(db_session, username="restore-target")

    await soft_delete_user(db_session, profile, user, admin_user_id=999)
    await db_session.refresh(user)
    await db_session.refresh(profile)
    pivot_user = user.tokens_invalidated_at
    pivot_profile = profile.tokens_invalidated_at
    assert pivot_user is not None
    assert pivot_profile is not None

    result = await restore_user(db_session, profile, user, admin_user_id=999)
    assert result == {"ok": True}

    await db_session.refresh(user)
    await db_session.refresh(profile)
    assert user.is_active is True
    assert profile.deleted_at is None
    assert profile.account_active is True
    # Pivots retained — previously issued JWTs stay rejected.
    assert user.tokens_invalidated_at == pivot_user
    assert profile.tokens_invalidated_at == pivot_profile


@pytest.mark.asyncio
async def test_set_account_active_true_does_not_clear_revocation_pivots(db_session):
    """Symmetric guarantee for ``set_account_active``: re-activation
    keeps the revocation stamp so the prior session window stays
    closed."""
    user, profile = await _make_user_with_profile(db_session, username="react-target")

    await set_account_active(
        db_session, profile, user, active=False, admin_user_id=999,
    )
    await db_session.refresh(user)
    await db_session.refresh(profile)
    pivot_user = user.tokens_invalidated_at
    pivot_profile = profile.tokens_invalidated_at
    assert pivot_user is not None
    assert pivot_profile is not None

    await set_account_active(
        db_session, profile, user, active=True, admin_user_id=999,
    )
    await db_session.refresh(user)
    await db_session.refresh(profile)
    assert user.is_active is True
    assert profile.account_active is True
    # No clearing on re-activation.
    assert user.tokens_invalidated_at == pivot_user
    assert profile.tokens_invalidated_at == pivot_profile


# ═══════════════════════════════════════════════════════════════════
# user search visibility
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_search_users_excludes_soft_deleted(client, db_session):
    me, _me_profile = await _make_user_with_profile(db_session, username="search-me")
    target, target_profile = await _make_user_with_profile(
        db_session, username="search-soft-deleted",
    )
    # Manually emulate a soft-deleted state: ``deleted_at`` set, both
    # active flags False (mirrors ``soft_delete_user``).
    target.is_active = False
    target_profile.deleted_at = datetime.now(timezone.utc)
    target_profile.account_active = False
    db_session.add_all([target, target_profile])
    await db_session.commit()

    _set_portal_cookie(client, me)
    resp = await client.get("/api/portal/profiles/search/users")
    assert resp.status_code == 200
    usernames = {item["display_name"] for item in resp.json()["items"]}
    assert "search-soft-deleted" not in usernames


@pytest.mark.asyncio
async def test_search_users_excludes_account_inactive(client, db_session):
    me, _me_profile = await _make_user_with_profile(db_session, username="search-me-2")
    target, target_profile = await _make_user_with_profile(
        db_session, username="search-deactivated",
    )
    # Drift scenario: ``User.is_active`` somehow stayed True while
    # ``UserProfile.account_active`` was flipped off.
    target_profile.account_active = False
    db_session.add(target_profile)
    await db_session.commit()

    _set_portal_cookie(client, me)
    resp = await client.get("/api/portal/profiles/search/users")
    assert resp.status_code == 200
    usernames = {item["display_name"] for item in resp.json()["items"]}
    assert "search-deactivated" not in usernames


@pytest.mark.asyncio
async def test_search_users_includes_active_user(client, db_session):
    me, _me_profile = await _make_user_with_profile(db_session, username="search-me-3")
    await _make_user_with_profile(db_session, username="search-friend")

    _set_portal_cookie(client, me)
    resp = await client.get("/api/portal/profiles/search/users")
    assert resp.status_code == 200
    usernames = {item["display_name"] for item in resp.json()["items"]}
    assert "search-friend" in usernames


# ═══════════════════════════════════════════════════════════════════
# public list owner visibility
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_public_lists_excludes_owner_soft_deleted(db_session):
    owner, owner_profile = await _make_user_with_profile(
        db_session, username="pl-soft-deleted-owner",
    )
    db_session.add(UserList(
        user_id=owner.id, name="Visible only when owner is active",
        privacy=PRIVACY_PUBLIC_READONLY,
    ))
    await db_session.commit()

    # Sanity: visible while active.
    visible_before = await get_public_lists(db_session, owner.id, limit=50)
    assert any(lst["owner_id"] == owner.id for lst in visible_before)

    owner.is_active = False
    owner_profile.deleted_at = datetime.now(timezone.utc)
    owner_profile.account_active = False
    db_session.add_all([owner, owner_profile])
    await db_session.commit()

    visible_after = await get_public_lists(db_session, owner.id, limit=50)
    assert all(lst["owner_id"] != owner.id for lst in visible_after)


@pytest.mark.asyncio
async def test_get_public_lists_excludes_owner_inactive(db_session):
    owner, owner_profile = await _make_user_with_profile(
        db_session, username="pl-deactivated-owner",
    )
    db_session.add(UserList(
        user_id=owner.id, name="Hidden when owner is deactivated",
        privacy=PRIVACY_COLLABORATIVE,
    ))
    await db_session.commit()

    owner_profile.account_active = False
    db_session.add(owner_profile)
    await db_session.commit()

    visible = await get_public_lists(db_session, owner.id, limit=50)
    assert all(lst["owner_id"] != owner.id for lst in visible)


@pytest.mark.asyncio
async def test_get_public_lists_includes_active_owner(db_session):
    owner, _ = await _make_user_with_profile(db_session, username="pl-active-owner")
    db_session.add(UserList(
        user_id=owner.id, name="Active and visible",
        privacy=PRIVACY_PUBLIC_READONLY,
    ))
    await db_session.commit()

    visible = await get_public_lists(db_session, owner.id, limit=50)
    assert any(
        lst["owner_id"] == owner.id and lst["name"] == "Active and visible"
        for lst in visible
    )


# ═══════════════════════════════════════════════════════════════════
# media rating author visibility
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_media_ratings_excludes_soft_deleted_author(db_session):
    author, author_profile = await _make_user_with_profile(
        db_session, username="rating-soft-deleted",
    )
    db_session.add(UserRating(
        user_id=author.id, tmdb_id=4242, media_type="movie",
        rating=8, review="Great",
    ))
    await db_session.commit()

    # Visible while author is active.
    before = await get_media_ratings(db_session, 4242, "movie")
    assert any(r["user_id"] == author.id for r in before)

    author.is_active = False
    author_profile.deleted_at = datetime.now(timezone.utc)
    author_profile.account_active = False
    db_session.add_all([author, author_profile])
    await db_session.commit()

    after = await get_media_ratings(db_session, 4242, "movie")
    assert all(r["user_id"] != author.id for r in after)


@pytest.mark.asyncio
async def test_get_media_ratings_excludes_inactive_author(db_session):
    author, author_profile = await _make_user_with_profile(
        db_session, username="rating-deactivated",
    )
    db_session.add(UserRating(
        user_id=author.id, tmdb_id=4243, media_type="movie",
        rating=5, review="Meh",
    ))
    await db_session.commit()

    author_profile.account_active = False
    db_session.add(author_profile)
    await db_session.commit()

    visible = await get_media_ratings(db_session, 4243, "movie")
    assert all(r["user_id"] != author.id for r in visible)


@pytest.mark.asyncio
async def test_get_media_ratings_includes_active_author(db_session):
    author, _ = await _make_user_with_profile(db_session, username="rating-active")
    db_session.add(UserRating(
        user_id=author.id, tmdb_id=4244, media_type="movie",
        rating=10, review="Loved it",
    ))
    await db_session.commit()

    visible = await get_media_ratings(db_session, 4244, "movie")
    assert any(
        r["user_id"] == author.id and r["review"] == "Loved it"
        for r in visible
    )


# ═══════════════════════════════════════════════════════════════════
# collaborative list contributors visibility
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_contributors_excludes_soft_deleted(db_session):
    owner, _ = await _make_user_with_profile(db_session, username="contrib-owner-1")
    contributor, contrib_profile = await _make_user_with_profile(
        db_session, username="contrib-soft-deleted",
    )
    lst = UserList(
        user_id=owner.id, name="Collab list",
        privacy=PRIVACY_COLLABORATIVE,
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)
    db_session.add(UserListContributor(list_id=lst.id, user_id=contributor.id))
    await db_session.commit()

    visible_before = await get_contributors(db_session, lst.id)
    assert any(c["user_id"] == contributor.id for c in visible_before)

    contributor.is_active = False
    contrib_profile.deleted_at = datetime.now(timezone.utc)
    contrib_profile.account_active = False
    db_session.add_all([contributor, contrib_profile])
    await db_session.commit()

    visible_after = await get_contributors(db_session, lst.id)
    assert all(c["user_id"] != contributor.id for c in visible_after)


@pytest.mark.asyncio
async def test_get_contributors_excludes_inactive(db_session):
    owner, _ = await _make_user_with_profile(db_session, username="contrib-owner-2")
    contributor, contrib_profile = await _make_user_with_profile(
        db_session, username="contrib-deactivated",
    )
    lst = UserList(
        user_id=owner.id, name="Collab list 2",
        privacy=PRIVACY_COLLABORATIVE,
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)
    db_session.add(UserListContributor(list_id=lst.id, user_id=contributor.id))
    await db_session.commit()

    contrib_profile.account_active = False
    db_session.add(contrib_profile)
    await db_session.commit()

    visible = await get_contributors(db_session, lst.id)
    assert all(c["user_id"] != contributor.id for c in visible)


@pytest.mark.asyncio
async def test_get_contributors_includes_active(db_session):
    owner, _ = await _make_user_with_profile(db_session, username="contrib-owner-3")
    contributor, _ = await _make_user_with_profile(
        db_session, username="contrib-active",
    )
    lst = UserList(
        user_id=owner.id, name="Collab list 3",
        privacy=PRIVACY_COLLABORATIVE,
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)
    db_session.add(UserListContributor(list_id=lst.id, user_id=contributor.id))
    await db_session.commit()

    visible = await get_contributors(db_session, lst.id)
    assert any(c["user_id"] == contributor.id for c in visible)
