"""Every sign-in is stamped on the profile, a member's as well as an admin's: the
admin "Users" page then shows a real last sign-in for everyone."""
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import event, select

from models.portal.profile import UserProfile

ADMIN_PASSWORD = "TestPassword123!"
RIGHT = "Right-Synthetic-1!"
AGENT = "TestBrowser/1.2.3"


async def _profile(db_session, user_id: int) -> UserProfile:
    return (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
        .execution_options(populate_existing=True)
    )).scalar_one()


@pytest_asyncio.fixture
async def member(make_user, db_session):
    """A member whose media-server password is RIGHT, with the Emby check mocked."""
    user = await make_user("member-a", role="viewer")
    emby_session = {"token": "rq-member-a", "user": user, "profile": await _profile(db_session, user.id)}

    async def _emby(db, username, password):
        return emby_session if password == RIGHT else None

    with patch("api.auth.login.authenticate_emby_user", new=AsyncMock(side_effect=_emby)), patch(
        "api.auth._portal.get_unread_news", new=AsyncMock(return_value=[]),
    ):
        yield user


@pytest.mark.parametrize("path", ["/api/auth/login", "/api/auth/portal-login"])
@pytest.mark.asyncio
async def test_an_admin_sign_in_is_stamped(client, admin_user, db_session, path):
    db_session.add(UserProfile(user_id=admin_user.id, display_name="admin", role="admin",
                               account_active=True, source="local"))
    await db_session.commit()

    with patch("api.auth._portal.get_unread_news", new=AsyncMock(return_value=[])):
        resp = await client.post(path, json={"username": "admin", "password": ADMIN_PASSWORD},
                                 headers={"User-Agent": AGENT})

    assert resp.status_code == 200, resp.text
    profile = await _profile(db_session, admin_user.id)
    assert profile.last_login_at is not None
    assert (profile.last_login_ip, profile.last_login_user_agent) == ("127.0.0.1", AGENT)


@pytest.mark.asyncio
async def test_a_member_sign_in_is_stamped_and_a_refused_one_is_not(client, member, db_session):
    refused = await client.post("/api/auth/portal-login", json={"username": "member-a", "password": "nope"})
    assert refused.status_code == 401
    assert (await _profile(db_session, member.id)).last_login_at is None

    resp = await client.post("/api/auth/portal-login", json={"username": "member-a", "password": RIGHT},
                             headers={"User-Agent": AGENT})

    assert (resp.status_code, resp.json()["scope"]) == (200, "portal")
    profile = await _profile(db_session, member.id)
    assert profile.last_login_at is not None
    assert (profile.last_login_ip, profile.last_login_user_agent) == ("127.0.0.1", AGENT)


@pytest.mark.asyncio
async def test_a_member_sign_in_survives_a_failed_stamp(client, member, db_session):
    engine = db_session.get_bind()
    failed = []

    def _fail_stamp(conn, cursor, statement, *_args):
        if statement.startswith("UPDATE user_profiles") and "last_login_ip" in statement:
            failed.append(statement)
            raise RuntimeError("simulated failure of the stamp's UPDATE")

    event.listen(engine, "before_cursor_execute", _fail_stamp)
    try:
        resp = await client.post("/api/auth/portal-login", json={"username": "member-a", "password": RIGHT})
    finally:
        event.remove(engine, "before_cursor_execute", _fail_stamp)

    assert failed, "the stamp never reached its UPDATE"
    assert (resp.status_code, resp.json()["username"]) == (200, "member-a")
