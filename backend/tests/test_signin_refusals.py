"""Sign-in refusals: nothing about an account shows before its password is
checked, only wrong passwords count, and odd input is refused up front."""
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import pytest
from sqlalchemy import delete, event, select

from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
from models.portal.profile import UserProfile
from models.security import SecurityAttempt, SecurityBlock
from models.user import User

ADMIN_PASSWORD = "TestPassword123!"


async def _failures(db_session) -> list[SecurityAttempt]:
    return (await db_session.execute(
        select(SecurityAttempt).where(SecurityAttempt.success == 0)
    )).scalars().all()


async def _add_user(db_session, name: str, password: str, *, active: bool = True) -> User:
    user = User(username=name, hashed_password=hash_password(password), is_active=active,
                must_change_password=False)
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_the_public_placeholder_is_a_wrong_password(client, db_session):
    """Imported accounts carry a known placeholder: typed on the admin sign-in,
    it must read like any wrong password, not tell which names are imported."""
    await _add_user(db_session, "member-a", EXTERNAL_AUTH_PASSWORD_SENTINEL)

    resp = await client.post("/api/auth/login", json={
        "username": "member-a", "password": EXTERNAL_AUTH_PASSWORD_SENTINEL,
    })

    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid_credentials"
    assert [f.scope for f in await _failures(db_session)] == ["admin"]


@pytest.mark.asyncio
async def test_the_placeholder_opens_no_admin_session_on_the_common_page(client, db_session, monkeypatch):
    """An imported account listed as admin: its public placeholder, typed on the
    page everyone uses, is a wrong password, never an admin session."""
    monkeypatch.setenv("MK_ADMIN_USERS", "admin,member-e")
    await _add_user(db_session, "member-e", EXTERNAL_AUTH_PASSWORD_SENTINEL)

    with patch("api.auth.login.authenticate_emby_user", new=AsyncMock(return_value=None)):
        resp = await client.post("/api/auth/portal-login", json={
            "username": "member-e", "password": EXTERNAL_AUTH_PASSWORD_SENTINEL,
        })

    assert (resp.status_code, resp.json()["detail"]) == (401, "invalid_credentials")
    assert "mk_token" not in resp.cookies
    assert [f.scope for f in await _failures(db_session)] == ["portal"]


@pytest.mark.asyncio
async def test_a_right_password_refused_by_the_admin_list_is_not_counted(client, db_session):
    await _add_user(db_session, "local-b", "Local-Synthetic-1!")

    for _ in range(3):
        resp = await client.post("/api/auth/login", json={"username": "local-b", "password": "Local-Synthetic-1!"})
        assert resp.json()["detail"] == "backoffice_forbidden"

    assert await _failures(db_session) == []
    assert (await db_session.execute(select(SecurityBlock))).scalars().all() == []


@pytest.mark.asyncio
async def test_a_disabled_admin_account_is_told_so_only_after_its_password(client, db_session, monkeypatch, caplog):
    """The right password of a disabled admin is refused, and leaves a trace."""
    monkeypatch.setenv("MK_ADMIN_USERS", "admin,old-admin")
    await _add_user(db_session, "old-admin", "Old-Synthetic-1!", active=False)

    with patch("api.auth.login.authenticate_emby_user", new=AsyncMock(return_value=None)), \
         caplog.at_level(logging.WARNING, logger="mediakeeper.api.auth"):
        wrong = await client.post("/api/auth/portal-login", json={"username": "old-admin", "password": "nope"})
        right = await client.post("/api/auth/portal-login", json={
            "username": "old-admin", "password": "Old-Synthetic-1!",
        })

    assert (wrong.status_code, wrong.json()["detail"]) == (401, "invalid_credentials")
    assert (right.status_code, right.json()["detail"]) == (403, "account_disabled")
    assert any("[PORTAL_LOGIN] Account disabled for user='old-admin'" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_the_media_server_check_refuses_a_disabled_account(db_session):
    """Emby may still accept the password of an account MediaKeeper disabled."""
    user = await _add_user(db_session, "member-d", EXTERNAL_AUTH_PASSWORD_SENTINEL, active=False)
    db_session.add(UserProfile(user_id=user.id, display_name="member-d", role="viewer", account_active=True,
                               tokens_invalidated_at=datetime.now(timezone.utc)))
    await db_session.commit()
    answer = AsyncMock(status_code=200)
    answer.json = lambda: {"User": {"Id": "emby-id-d"}}
    http = AsyncMock()
    http.post = AsyncMock(return_value=answer)

    with patch("services.portal.emby_auth.get_active_media_source", new=AsyncMock(return_value={
        "source": "emby", "url": "http://emby.test", "api_key": "key",
    })), patch("services.portal.emby_auth.get_internal_client", return_value=http):
        from services.portal.emby_auth import AccountInactive, authenticate_emby_user
        with pytest.raises(AccountInactive):
            await authenticate_emby_user(db_session, "member-d", "any")


@pytest.mark.parametrize("name", ["bad\x00name", "bad\nname", "   ", "İ" * 51])
@pytest.mark.parametrize("path", ["/api/auth/login", "/api/auth/portal-login"])
@pytest.mark.asyncio
async def test_odd_names_are_refused_before_any_check(client, db_session, path, name):
    """A blank name escapes the per-name counter, control characters forge log
    lines or break the database query, and some capitals grow when lower-cased
    past the 100 characters a name is stored in."""
    resp = await client.post(path, json={"username": name, "password": "whatever"})

    assert resp.status_code == 422
    assert await _failures(db_session) == []


@pytest.mark.asyncio
async def test_a_name_that_still_fits_once_lower_cased_is_checked(client, db_session):
    with patch("api.auth.login.authenticate_emby_user", new=AsyncMock(return_value=None)):
        resp = await client.post("/api/auth/portal-login", json={"username": "İ" * 50, "password": "x"})

    assert resp.status_code == 401
    assert len(await _failures(db_session)) == 1


@pytest.mark.parametrize("path", ["/api/auth/login", "/api/auth/portal-login"])
@pytest.mark.asyncio
async def test_admin_sign_in_survives_a_failed_profile_stamp(client, admin_user, db_session, path):
    """The stamp's commit fails in its flush, which expires every loaded object:
    the sign-in must still answer without reading them again."""
    db_session.add(UserProfile(user_id=admin_user.id, display_name="admin", role="admin",
                               account_active=True, source="local"))
    await db_session.commit()
    engine = db_session.get_bind()
    failed = []

    def _fail_stamp(conn, cursor, statement, *_args):
        if statement.startswith("UPDATE user_profiles") and "last_login_ip" in statement:
            failed.append(statement)
            raise RuntimeError("simulated failure of the stamp's UPDATE")

    event.listen(engine, "before_cursor_execute", _fail_stamp)
    try:
        with patch("api.auth._portal.get_unread_news", new=AsyncMock(return_value=[])):
            resp = await client.post(path, json={"username": "admin", "password": ADMIN_PASSWORD})
    finally:
        event.remove(engine, "before_cursor_execute", _fail_stamp)

    assert failed, "the stamp never reached its UPDATE"
    assert resp.status_code == 200, resp.text
    assert resp.json()["username"] == "admin"
    assert resp.json()["must_change_password"] is False


@pytest.mark.asyncio
async def test_an_admin_name_costs_the_same_with_or_without_an_account(
    client, admin_user, db_session, monkeypatch,
):
    """Two bcrypt rounds either way, in any casing: the time a refused try takes
    must not tell whether a listed admin name has an account."""
    monkeypatch.setenv("MK_ADMIN_USERS", "admin,ghost-admin")
    rounds = {}
    with patch("api.auth.login.authenticate_emby_user", new=AsyncMock(return_value=None)):
        for name in ("admin", "ADMIN", "ghost-admin", "GHOST-ADMIN"):
            # Every try starts with no failure on record, so no block cuts it short.
            await db_session.execute(delete(SecurityAttempt))
            await db_session.execute(delete(SecurityBlock))
            await db_session.commit()
            checkpw = MagicMock(wraps=bcrypt.checkpw)
            with patch.object(bcrypt, "checkpw", checkpw):
                resp = await client.post("/api/auth/portal-login", json={
                    "username": name, "password": "Wrong-Synthetic-1!",
                })
            assert resp.status_code == 401
            rounds[name] = checkpw.call_count

    assert rounds == {"admin": 2, "ADMIN": 2, "ghost-admin": 2, "GHOST-ADMIN": 2}
