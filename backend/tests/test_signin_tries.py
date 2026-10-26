"""Three real tries per name on the sign-in page (/api/auth/portal-login).

Every try reaches the password check until the name is blocked, one member's
failures never refuse another member on the same address before the address
threshold, a successful sign-in stops that name's earlier failures from
counting, and an admin name's refused tries count against its local password.
"""
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
from models.portal.profile import UserProfile
from models.security import SecurityAttempt, SecurityBlock
from models.user import User
from services.security import create_block

RIGHT = "Right-Synthetic-1!"
WRONG = "Wrong-Synthetic-1!"
ADMIN_PASSWORD = "TestPassword123!"


@pytest.fixture
def members(make_user, db_session):
    """Members whose media-server password is RIGHT, with the Emby check mocked."""
    sessions = {}

    async def _add(name: str):
        user = await make_user(name, role="viewer")
        profile = (await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )).scalar_one()
        sessions[name] = {"token": f"rq-{name}", "user": user, "profile": profile}

    async def _emby(db, username, password):
        return sessions.get(username.lower()) if password == RIGHT else None

    emby = AsyncMock(side_effect=_emby)
    with patch("api.auth.login.authenticate_emby_user", new=emby), patch(
        "api.auth._portal.get_unread_news", new=AsyncMock(return_value=[]),
    ):
        yield _add, emby


async def _sign_in(client, name: str, password: str) -> int:
    resp = await client.post("/api/auth/portal-login", json={"username": name, "password": password})
    return resp.status_code


async def _failures(db_session, scope: str) -> list[SecurityAttempt]:
    return (await db_session.execute(
        select(SecurityAttempt).where(SecurityAttempt.scope == scope, SecurityAttempt.success == 0)
        .order_by(SecurityAttempt.id)
    )).scalars().all()


@pytest.mark.asyncio
async def test_right_password_on_the_third_try_is_accepted(client, members):
    add, emby = members
    await add("member-a")

    codes = [await _sign_in(client, "member-a", p) for p in (WRONG, WRONG, RIGHT)]

    assert codes == [401, 401, 200]
    assert emby.await_count == 3


@pytest.mark.asyncio
async def test_a_member_is_not_refused_for_another_members_failures(client, members):
    """Two failures from member A leave member B free on the same address; the
    third one reaches the address threshold, kept at three."""
    add, _ = members
    await add("member-a")
    await add("member-b")

    assert [await _sign_in(client, "member-a", WRONG) for _ in range(2)] == [401, 401]
    assert await _sign_in(client, "member-b", RIGHT) == 200
    assert await _sign_in(client, "member-a", WRONG) == 401
    assert await _sign_in(client, "member-b", RIGHT) == 429


@pytest.mark.asyncio
async def test_a_successful_sign_in_resets_the_name(client, members, db_session):
    add, _ = members
    await add("member-a")

    codes = [await _sign_in(client, "member-a", p) for p in (WRONG, WRONG, RIGHT, WRONG, WRONG)]

    assert codes == [401, 401, 200, 401, 401]
    assert (await db_session.execute(select(SecurityBlock))).scalars().all() == []
    cleared = [f.cleared_at is not None for f in await _failures(db_session, "portal")]
    assert cleared == [True, True, False, False]


@pytest.mark.asyncio
async def test_admin_password_misses_count_against_the_admin_name(client, admin_user, members, db_session):
    """On the page everyone uses, three wrong passwords for an admin name block
    it like on the admin sign-in: the right local password then waits too."""
    assert [await _sign_in(client, "admin", WRONG) for _ in range(3)] == [401, 401, 401]
    assert await _sign_in(client, "admin", ADMIN_PASSWORD) == 429

    assert len(await _failures(db_session, "admin")) == 3
    assert await _failures(db_session, "portal") == []


@pytest.mark.asyncio
async def test_a_portal_block_does_not_hide_admin_password_misses(client, admin_user, members, db_session):
    """Refused at the portal gate after a wrong local password, the try still
    counts against the admin name."""
    await create_block(db_session, admin_id=None, ip=None, username="admin", scope="portal", permanent=True)

    assert [await _sign_in(client, "admin", WRONG) for _ in range(3)] == [429, 429, 429]
    assert await _sign_in(client, "admin", ADMIN_PASSWORD) == 429
    assert len(await _failures(db_session, "admin")) == 3


@pytest.mark.asyncio
async def test_an_emby_success_does_not_count_against_the_admin_name(client, admin_user, members, db_session):
    """An admin who signs in with the media-server password gets the portal and
    leaves no failure on the local password."""
    db_session.add(UserProfile(user_id=admin_user.id, display_name="admin", role="admin", account_active=True))
    await db_session.commit()
    profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == admin_user.id)
    )).scalar_one()
    emby_session = {"token": "rq-admin", "user": admin_user, "profile": profile}

    with patch("api.auth.login.authenticate_emby_user", new=AsyncMock(return_value=emby_session)):
        resp = await client.post("/api/auth/portal-login", json={"username": "admin", "password": RIGHT})

    assert resp.status_code == 200
    assert resp.json()["scope"] == "portal"
    assert await _failures(db_session, "admin") == []


@pytest.mark.asyncio
async def test_an_imported_account_listed_as_admin_keeps_the_emby_counter(
    client, members, db_session, monkeypatch,
):
    """With no local password, its tries are about its Emby password: an Emby
    success resets them like any member's."""
    monkeypatch.setenv("MK_ADMIN_USERS", "admin,member-e")
    add, _ = members
    await add("member-e")
    user = (await db_session.execute(select(User).where(User.username == "member-e"))).scalar_one()
    user.hashed_password = hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL)
    await db_session.commit()

    codes = [await _sign_in(client, "member-e", p) for p in (WRONG, WRONG, RIGHT, WRONG, WRONG)]

    assert codes == [401, 401, 200, 401, 401]
    assert await _failures(db_session, "admin") == []
    assert (await db_session.execute(select(SecurityBlock))).scalars().all() == []


@pytest.mark.asyncio
async def test_a_password_change_resets_the_failed_tries(authed_client, db_session):
    """Wrong current passwords count until a change succeeds, then start again."""
    async def change(current: str, new: str) -> int:
        resp = await authed_client.post("/api/auth/change-password", json={
            "current_password": current, "new_password": new, "confirm_password": new,
        })
        return resp.status_code

    new_password = "Changed-Synthetic-2!"
    assert [await change(WRONG, new_password) for _ in range(2)] == [400, 400]
    assert await change(ADMIN_PASSWORD, new_password) == 200
    assert [await change(WRONG, "Changed-Synthetic-3!") for _ in range(2)] == [400, 400]

    assert (await db_session.execute(select(SecurityBlock))).scalars().all() == []
    cleared = [f.cleared_at is not None for f in await _failures(db_session, "admin_password")]
    assert cleared == [True, True, False, False]
