"""Every sign-in is stamped on the profile, a member's as well as an admin's: the
admin "Users" page then shows a real last sign-in for everyone."""
import logging
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import event, select

from models.portal.profile import UserProfile
from models.user import User

ADMIN_PASSWORD = "TestPassword123!"
RIGHT = "Right-Synthetic-1!"
AGENT = "TestBrowser/1.2.3"


async def _profile(db, user_id: int) -> UserProfile:
    return (await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
        .execution_options(populate_existing=True)
    )).scalar_one()


@contextmanager
def _failing_update(db_session, column: str):
    """Fail the UPDATE of a profile that writes ``column``, as in a commit's flush."""
    engine = db_session.get_bind()
    failed = []

    def _fail(conn, cursor, statement, *_args):
        if statement.startswith("UPDATE user_profiles") and f"{column}=" in statement:
            failed.append(statement)
            raise RuntimeError(f"simulated failure of the {column} update")

    event.listen(engine, "before_cursor_execute", _fail)
    try:
        yield failed
    finally:
        event.remove(engine, "before_cursor_execute", _fail)


@pytest_asyncio.fixture
async def member(make_user):
    """A member whose media-server password is RIGHT. The mocked check loads the
    account in the request's session, as the real one does: a failed flush then
    expires what the route holds."""
    user = await make_user("member-a", role="viewer")
    user_id = user.id

    async def _emby(db, username, password):
        if password != RIGHT:
            return None
        return {"token": "rq-member-a", "user": await db.get(User, user_id), "profile": await _profile(db, user_id)}

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
    with _failing_update(db_session, "last_login_ip") as failed:
        resp = await client.post("/api/auth/portal-login", json={"username": "member-a", "password": RIGHT})

    assert failed, "the stamp never reached its UPDATE"
    assert (resp.status_code, resp.json()["username"]) == (200, "member-a")


@pytest.mark.asyncio
async def test_a_failed_xp_grant_is_logged_and_keeps_the_stamp(client, member, db_session, caplog):
    """The sign-in goes on, and the stamp behind the XP finds a usable session."""
    with _failing_update(db_session, "xp") as failed, caplog.at_level(logging.ERROR, logger="mediakeeper.api.auth"):
        resp = await client.post("/api/auth/portal-login", json={"username": "member-a", "password": RIGHT})

    assert failed, "the XP grant never reached its UPDATE"
    assert resp.status_code == 200, resp.text
    assert (await _profile(db_session, member.id)).last_login_at is not None
    assert any(f"Daily XP failed for user_id={member.id}" in r.getMessage() for r in caplog.records)
