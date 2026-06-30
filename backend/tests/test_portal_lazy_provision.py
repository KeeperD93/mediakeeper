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
from services.portal._pseudo_words import generate_pseudo
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
async def test_ensure_user_stores_generated_pseudo_not_emby_login(db_session):
    """The provisioned profile stores a generated pseudo, never the raw
    Emby login — which stays on ``User.username`` for operators."""
    user = await ensure_user_for_emby_session(
        db_session, emby_username="secret_emby_login", emby_user_id="EMBY-555",
    )
    profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )).scalar_one()
    assert user.username == "secret_emby_login"  # login preserved for operators
    assert profile.display_name == generate_pseudo(user.id, "fr")
    assert profile.display_name != "secret_emby_login"
    assert profile.display_name_must_set is True


@pytest.mark.asyncio
async def test_ensure_user_returns_none_for_empty_username(db_session):
    assert await ensure_user_for_emby_session(db_session, emby_username="") is None
    assert await ensure_user_for_emby_session(db_session, emby_username=None) is None


@pytest.mark.asyncio
async def test_ensure_user_savepoint_swallows_concurrent_provision(db_session, monkeypatch):
    """Two playback observations of the same Emby login can both pass the
    existing-account lookup, then both INSERT the same username — one wins,
    the other trips the unique constraint. Single-process we reproduce that
    by pre-inserting the winner and monkeypatching the lookup to miss it
    (the TOCTOU window). The losing call must recover the winner's row via
    the SAVEPOINT rollback instead of poisoning the session.
    """
    from services.portal import user_import as ui_mod

    winner = User(username="racer", hashed_password="x", is_active=True)
    db_session.add(winner)
    await db_session.commit()
    await db_session.refresh(winner)

    async def _pretend_absent(_db, *, emby_username, emby_user_id):
        return None

    monkeypatch.setattr(ui_mod, "_find_existing_emby_user", _pretend_absent)

    result = await ensure_user_for_emby_session(
        db_session, emby_username="racer", emby_user_id="EMBY-RACE",
    )
    assert result is not None
    assert result.id == winner.id

    # Sentinel write proves the outer transaction survived the savepoint
    # rollback — without the SAVEPOINT this commit would explode.
    db_session.add(User(username="sentinel", hashed_password="x", is_active=True))
    await db_session.commit()

    count = (await db_session.execute(
        select(func.count(User.id)).where(func.lower(User.username) == "racer")
    )).scalar_one()
    assert count == 1
