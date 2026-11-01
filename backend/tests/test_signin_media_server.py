"""What the media server answers decides how a sign-in ends: a refused password
counts, a server that cannot judge one never does, and nothing tells a member's
account apart before the server has accepted the password."""
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy import select

from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
from models.portal.profile import UserProfile
from models.security import SecurityAttempt, SecurityBlock
from models.user import User
from services.portal.emby_auth import (
    AccountInactive,
    MediaServerUnavailable,
    authenticate_emby_user,
)

EMBY = {"source": "emby", "url": "http://emby.test", "api_key": "key"}
WRONG = "Wrong-Synthetic-1!"
ADMIN_PASSWORD = "TestPassword123!"
ACCEPTED = httpx.Response(200, json={"User": {"Id": "emby-id-a"}})


@contextmanager
def _media_server(answer=None, *, raises=None, source=EMBY):
    http = AsyncMock()
    http.post = AsyncMock(return_value=answer, side_effect=raises)
    with patch("services.portal.emby_auth.get_active_media_source", new=AsyncMock(return_value=source)), \
         patch("services.portal.emby_auth.get_internal_client", return_value=http), \
         patch("api.auth._portal.get_unread_news", new=AsyncMock(return_value=[])):
        yield http


async def _add_member(db_session, name="member-a", *, emby_id=None, active=True, account_active=True, **profile):
    user = User(username=name, hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
                is_active=active, must_change_password=False)
    db_session.add(user)
    await db_session.commit()
    db_session.add(UserProfile(user_id=user.id, display_name=name, role="viewer",
                               account_active=account_active, emby_user_id=emby_id, **profile))
    await db_session.commit()
    return user


async def _failures(db_session) -> list[str]:
    return list((await db_session.execute(
        select(SecurityAttempt.scope).where(SecurityAttempt.success == 0)
    )).scalars().all())


async def _sign_in(client, name="member-a", password=WRONG):
    return await client.post("/api/auth/portal-login", json={"username": name, "password": password})


@pytest.mark.parametrize("source", [
    None,
    {"source": "other", "url": "http://other.test", "api_key": "key"},
    {"source": "emby", "url": "", "api_key": "key"},
    {"source": "emby", "url": "http://emby.test", "api_key": ""},
])
@pytest.mark.asyncio
async def test_no_usable_media_server_is_said_without_asking_anyone(db_session, source):
    with _media_server(source=source) as http, pytest.raises(MediaServerUnavailable) as refused:
        await authenticate_emby_user(db_session, "member-a", WRONG)

    assert refused.value.code == "media_server_not_configured"
    http.post.assert_not_awaited()


@pytest.mark.parametrize("error", [
    httpx.ConnectError("refused"),
    httpx.ConnectTimeout("slow"),
    httpx.ReadTimeout("slow"),
    httpx.RemoteProtocolError("cut"),
    httpx.InvalidURL("bad address"),
])
@pytest.mark.asyncio
async def test_no_answer_is_unreachable(db_session, error):
    with _media_server(raises=error), pytest.raises(MediaServerUnavailable) as refused:
        await authenticate_emby_user(db_session, "member-a", WRONG)

    assert refused.value.code == "media_server_unreachable"


@pytest.mark.parametrize("status", [502, 503, 504])
@pytest.mark.asyncio
async def test_a_server_that_says_it_is_down_is_unreachable(db_session, status):
    with _media_server(httpx.Response(status)), pytest.raises(MediaServerUnavailable) as refused:
        await authenticate_emby_user(db_session, "member-a", WRONG)

    assert refused.value.code == "media_server_unreachable"


@pytest.mark.parametrize("answer", [
    httpx.Response(200, content=b"<html>a proxy page</html>"),
    httpx.Response(200, json=[]),
    httpx.Response(200, json={}),
    httpx.Response(200, json={"User": None}),
    httpx.Response(200, json={"User": {}}),
    httpx.Response(200, json={"User": {"Id": ""}}),
    httpx.Response(200, json={"User": {"Id": 12}}),
])
@pytest.mark.asyncio
async def test_a_200_that_names_nobody_signs_nobody_in(db_session, answer):
    """A name that matches an account must not be enough: only the server's own
    answer vouches for the password."""
    await _add_member(db_session)

    with _media_server(answer), pytest.raises(MediaServerUnavailable) as refused:
        await authenticate_emby_user(db_session, "member-a", WRONG)

    assert refused.value.code == "media_server_unreachable"


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500])
@pytest.mark.asyncio
async def test_any_other_status_reads_as_a_wrong_password(db_session, caplog, status):
    """A status nobody checked by hand must not open unlimited guessing."""
    with _media_server(httpx.Response(status)), caplog.at_level(logging.WARNING, "mediakeeper.portal.emby_auth"):
        assert await authenticate_emby_user(db_session, "member-a", WRONG) is None

    assert any(f"HTTP {status}" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_a_member_renamed_on_the_media_server_is_found_by_id(db_session):
    await _add_member(db_session, "old-name", emby_id="emby-id-a")

    with _media_server(ACCEPTED):
        session = await authenticate_emby_user(db_session, "new-name", "any")

    assert session["user"].username == "old-name"


@pytest.mark.asyncio
async def test_an_accented_capital_is_found_by_id(db_session):
    """The test database lower-cases only plain letters, so the name alone misses."""
    await _add_member(db_session, "Émile", emby_id="emby-id-a")

    with _media_server(ACCEPTED):
        session = await authenticate_emby_user(db_session, "Émile", "any")

    assert session["user"].username == "Émile"


@pytest.mark.asyncio
async def test_a_profile_without_an_id_is_found_by_name_and_gets_it(db_session):
    await _add_member(db_session, "Member-A")

    with _media_server(ACCEPTED):
        session = await authenticate_emby_user(db_session, "member-a", "any")

    assert session["profile"].emby_user_id == "emby-id-a"


@pytest.mark.parametrize("flags", [{"active": False}, {"account_active": False}])
@pytest.mark.asyncio
async def test_a_disabled_account_is_inactive(db_session, flags):
    await _add_member(db_session, **flags)

    with _media_server(ACCEPTED), pytest.raises(AccountInactive):
        await authenticate_emby_user(db_session, "member-a", "any")


@pytest.mark.asyncio
async def test_an_expired_account_is_inactive_and_switched_off(db_session):
    await _add_member(db_session, access_end_date=datetime.now(timezone.utc) - timedelta(days=1))

    with _media_server(ACCEPTED), pytest.raises(AccountInactive):
        await authenticate_emby_user(db_session, "member-a", "any")

    profile = (await db_session.execute(select(UserProfile))).scalar_one()
    await db_session.refresh(profile)
    assert profile.account_active is False


@pytest.mark.asyncio
async def test_a_media_server_down_costs_no_try(client, db_session):
    """Three tries during a breakdown block nobody, and the member gets in once it is back."""
    await _add_member(db_session)

    with _media_server(raises=httpx.ConnectError("refused")):
        answers = [await _sign_in(client) for _ in range(3)]

    assert [(a.status_code, a.json()["detail"]) for a in answers] == [(503, "media_server_unreachable")] * 3
    assert await _failures(db_session) == []
    assert (await db_session.execute(select(SecurityBlock))).scalars().all() == []

    with _media_server(ACCEPTED):
        assert (await _sign_in(client, password="any")).status_code == 200


@pytest.mark.asyncio
async def test_no_media_server_says_so_and_costs_no_try(client, db_session):
    with _media_server(source=None):
        resp = await _sign_in(client)

    assert (resp.status_code, resp.json()["detail"]) == (503, "media_server_not_configured")
    assert await _failures(db_session) == []


@pytest.mark.parametrize("media_server", [
    {"raises": httpx.ConnectError("refused")},
    {"source": None},
])
@pytest.mark.parametrize("name", ["admin", "ghost-admin"])
@pytest.mark.asyncio
async def test_an_admin_miss_still_counts_without_a_media_server(
    client, admin_user, db_session, monkeypatch, media_server, name,
):
    """The local password was checked and wrong: an install with no media server
    must not answer "no server" for a typo, nor let guesses go uncounted. A listed
    name with no account behaves the same."""
    monkeypatch.setenv("MK_ADMIN_USERS", "admin,ghost-admin")

    with _media_server(**media_server):
        resp = await _sign_in(client, name)

    assert (resp.status_code, resp.json()["detail"]) == (401, "invalid_credentials")
    assert await _failures(db_session) == ["admin"]


@pytest.mark.asyncio
async def test_an_admin_right_password_needs_no_media_server(client, admin_user):
    with _media_server(raises=httpx.ConnectError("refused")) as http:
        resp = await _sign_in(client, "admin", ADMIN_PASSWORD)

    assert resp.status_code == 200
    http.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_an_imported_account_listed_as_admin_has_no_local_password_to_count(
    client, db_session, monkeypatch,
):
    monkeypatch.setenv("MK_ADMIN_USERS", "admin,member-a")
    await _add_member(db_session)

    with _media_server(raises=httpx.ConnectError("refused")):
        resp = await _sign_in(client)

    assert (resp.status_code, resp.json()["detail"]) == (503, "media_server_unreachable")
    assert await _failures(db_session) == []


@pytest.mark.asyncio
async def test_an_inactive_account_is_told_only_once_its_password_is_accepted(client, db_session):
    await _add_member(db_session, active=False)

    with _media_server(httpx.Response(401)):
        wrong = await _sign_in(client)
    assert (wrong.status_code, wrong.json()["detail"]) == (401, "invalid_credentials")
    assert await _failures(db_session) == ["portal"]

    with _media_server(ACCEPTED):
        right = await _sign_in(client, password="any")
    assert (right.status_code, right.json()["detail"]) == (403, "account_disabled")
    assert await _failures(db_session) == ["portal"]


@pytest.mark.asyncio
async def test_an_account_never_imported_reads_like_a_wrong_password(client, db_session):
    """Told apart, the page would confirm the password of any media-server account."""
    with _media_server(ACCEPTED):
        resp = await _sign_in(client, "never-imported", "any")

    assert (resp.status_code, resp.json()["detail"]) == (401, "invalid_credentials")
    assert await _failures(db_session) == ["portal"]


@pytest.mark.asyncio
async def test_an_unexpected_status_counts_as_a_try(client, db_session):
    with _media_server(httpx.Response(500)):
        resp = await _sign_in(client)

    assert (resp.status_code, resp.json()["detail"]) == (401, "invalid_credentials")
    assert await _failures(db_session) == ["portal"]
