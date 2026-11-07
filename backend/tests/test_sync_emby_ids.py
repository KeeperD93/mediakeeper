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


async def _profile(db, name: str, *, source: str) -> int:
    user = User(username=name, hashed_password="x", is_active=True, must_change_password=False)
    db.add(user)
    await db.flush()
    db.add(UserProfile(user_id=user.id, display_name=name, role="viewer", account_active=True, source=source))
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
