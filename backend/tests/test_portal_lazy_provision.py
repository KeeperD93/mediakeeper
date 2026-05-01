"""Lazy provisioning of MediaKeeper accounts from Emby playback sessions.

A user observed by the playback collector who has no MediaKeeper row
yet should get one created on the spot. XP only lands once an admin
activates the account.
"""
from __future__ import annotations

import pytest
from sqlalchemy import func, select

from models.portal.profile import UserProfile
from models.user import User
from services.portal.user_import import ensure_user_for_emby_session


@pytest.mark.asyncio
async def test_ensure_user_creates_inactive_account_on_first_sight(db_session):
    user = await ensure_user_for_emby_session(
        db_session, emby_username="alice", emby_user_id="EMBY-123",
    )
    assert user is not None
    assert user.username == "alice"

    profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )).scalar_one_or_none()
    assert profile is not None
    assert profile.account_active is False
    assert profile.display_name_must_set is True
    assert profile.role == "viewer"
    assert profile.avatar_url == "/api/emby/user-image/EMBY-123"


@pytest.mark.asyncio
async def test_ensure_user_returns_existing_without_changes(db_session):
    first = await ensure_user_for_emby_session(
        db_session, emby_username="bob", emby_user_id="EMBY-777",
    )
    profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == first.id)
    )).scalar_one()
    profile.display_name = "BobChosen"
    profile.display_name_must_set = False
    db_session.add(profile)
    await db_session.commit()

    again = await ensure_user_for_emby_session(
        db_session, emby_username="bob", emby_user_id="EMBY-777",
    )
    assert again.id == first.id

    refreshed = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == first.id)
    )).scalar_one()
    assert refreshed.display_name == "BobChosen"
    assert refreshed.display_name_must_set is False


@pytest.mark.asyncio
async def test_ensure_user_prefers_stable_emby_id_over_session_name(db_session):
    user = User(
        username="portal-alice",
        hashed_password="x",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    db_session.add(UserProfile(
        user_id=user.id,
        display_name="Alice",
        role="viewer",
        account_active=True,
        emby_user_id="EMBY-42",
    ))
    await db_session.commit()

    found = await ensure_user_for_emby_session(
        db_session,
        emby_username="Alice From Emby",
        emby_user_id="EMBY-42",
    )

    assert found.id == user.id
    user_count = (await db_session.execute(
        select(func.count(User.id))
    )).scalar_one()
    assert user_count == 1


@pytest.mark.asyncio
async def test_ensure_user_backfills_emby_id_for_existing_username(db_session):
    user = User(
        username="carol",
        hashed_password="x",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    db_session.add(UserProfile(
        user_id=user.id,
        display_name="Carol",
        role="viewer",
        account_active=True,
    ))
    await db_session.commit()

    found = await ensure_user_for_emby_session(
        db_session,
        emby_username="carol",
        emby_user_id="EMBY-99",
    )

    assert found.id == user.id
    profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )).scalar_one()
    assert profile.emby_user_id == "EMBY-99"
    assert profile.avatar_url == "/api/emby/user-image/EMBY-99"


@pytest.mark.asyncio
async def test_ensure_user_resolves_display_name_collision(db_session):
    a = User(
        username="reused",
        hashed_password="x",
        is_active=True,
    )
    db_session.add(a)
    await db_session.commit()
    await db_session.refresh(a)

    db_session.add(UserProfile(
        user_id=a.id,
        display_name="reused",
        role="viewer",
        account_active=False,
    ))
    await db_session.commit()

    new_user = await ensure_user_for_emby_session(
        db_session, emby_username="reused2",
    )
    profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == new_user.id)
    )).scalar_one()
    assert profile.display_name == "reused2"


@pytest.mark.asyncio
async def test_ensure_user_returns_none_for_empty_username(db_session):
    assert await ensure_user_for_emby_session(db_session, emby_username="") is None
    assert await ensure_user_for_emby_session(db_session, emby_username=None) is None
