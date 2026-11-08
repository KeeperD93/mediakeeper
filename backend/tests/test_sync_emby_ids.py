"""The "Sync Emby ids" action links Emby profiles by name and leaves local accounts alone."""
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.portal.profile import UserProfile
from models.user import User
from services.portal.admin_users_emby import backfill_emby_user_ids
from services.portal.xp import account_earns

EMBY_USERS = [
    {"Id": "emby-12345", "Name": "admin", "ConnectUserName": "admin@example.com", "Policy": {"IsDisabled": True}},
    {"Id": "emby-67890", "Name": "alice", "ConnectUserName": "alice@example.com", "Policy": {"IsDisabled": False}},
]


async def _profile(db, name: str, *, source: str, emby_user_id: str | None = None) -> int:
    user = User(username=name, hashed_password="x", is_active=True, must_change_password=False)
    db.add(user)
    await db.flush()
    db.add(UserProfile(
        user_id=user.id, display_name=name, role="viewer", account_active=True, source=source,
        emby_user_id=emby_user_id,
    ))
    await db.commit()
    return user.id


async def _link(db, user_id: int) -> tuple:
    db.expire_all()
    return (await db.execute(
        select(UserProfile.source, UserProfile.emby_user_id, UserProfile.emby_is_disabled, UserProfile.email)
        .where(UserProfile.user_id == user_id)
    )).one()


@pytest.mark.asyncio
async def test_a_local_account_bearing_an_emby_name_is_never_linked(db_session):
    admin = await _profile(db_session, "Admin", source="local")
    alice = await _profile(db_session, "alice", source="emby")

    with patch("services.portal.admin_users_emby.list_emby_users", new=AsyncMock(return_value=EMBY_USERS)):
        result = await backfill_emby_user_ids(db_session)

    assert (result["updated"], result["already_linked"], result["unmatched"]) == (1, 0, 0)
    assert tuple(await _link(db_session, admin)) == ("local", None, None, None)
    assert await account_earns(db_session, admin) is False
    assert tuple(await _link(db_session, alice)) == ("emby", "emby-67890", False, "alice@example.com")
    assert await account_earns(db_session, alice) is True


@pytest.mark.asyncio
async def test_an_emby_id_held_by_another_profile_is_never_given(db_session):
    # Bob's Emby account now bears Carl's name: by name alone, Carl would get it too.
    carl = await _profile(db_session, "Carl", source="emby", emby_user_id="emby-gone")
    bob = await _profile(db_session, "Bob", source="emby", emby_user_id="emby-bob")
    renamed = [{"Id": "emby-bob", "Name": "Carl", "Policy": {"IsDisabled": True}}]

    with patch("services.portal.admin_users_emby.list_emby_users", new=AsyncMock(return_value=renamed)):
        result = await backfill_emby_user_ids(db_session)

    assert (result["updated"], result["already_linked"], result["unmatched"]) == (0, 0, 2)
    carl_link = await _link(db_session, carl)
    assert (carl_link.emby_user_id, carl_link.emby_is_disabled) == ("emby-gone", None)
    assert (await _link(db_session, bob)).emby_user_id == "emby-bob"


@pytest.mark.asyncio
async def test_one_pass_never_gives_the_same_emby_id_twice(db_session):
    first = await _profile(db_session, "Bob", source="emby")
    second = await _profile(db_session, "bob", source="emby")
    emby = [{"Id": "emby-bob", "Name": "bob", "Policy": {}}]

    with patch("services.portal.admin_users_emby.list_emby_users", new=AsyncMock(return_value=emby)):
        result = await backfill_emby_user_ids(db_session)

    assert (result["updated"], result["unmatched"]) == (1, 1)
    linked = {(await _link(db_session, user_id)).emby_user_id for user_id in (first, second)}
    assert linked == {"emby-bob", None}


@pytest.mark.asyncio
async def test_a_profile_keeps_syncing_with_its_own_id_or_a_free_one(db_session):
    # The profile's own id stays usable, and Emby reinstalled gives a new id nobody holds.
    alice = await _profile(db_session, "alice", source="emby", emby_user_id="emby-67890")
    bob = await _profile(db_session, "bob", source="emby", emby_user_id="emby-old")
    emby = [
        {"Id": "emby-67890", "Name": "alice", "Policy": {"IsDisabled": False}},
        {"Id": "emby-new", "Name": "bob", "Policy": {"IsDisabled": False}},
    ]

    with patch("services.portal.admin_users_emby.list_emby_users", new=AsyncMock(return_value=emby)):
        result = await backfill_emby_user_ids(db_session)

    assert result["unmatched"] == 0
    assert (await _link(db_session, alice)).emby_user_id == "emby-67890"
    assert (await _link(db_session, bob)).emby_user_id == "emby-new"
