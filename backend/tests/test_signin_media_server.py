"""What the media server answers decides how a sign-in ends: a refused password
counts, and a server that cannot judge one never does."""
import logging

import httpx
import pytest
from sqlalchemy import select

from models.security import SecurityBlock
from services.portal.emby_auth import MediaServerUnavailable, authenticate_emby_user
from tests._signin_media_server_helpers import (
    ACCEPTED,
    ADMIN_PASSWORD,
    WRONG,
    add_member,
    failures,
    media_server,
    sign_in,
)

NO_ASCII_KEY = UnicodeEncodeError("ascii", "é", 0, 1, "ordinal not in range(128)")


@pytest.mark.parametrize("source", [
    None,
    {"source": "other", "url": "http://other.test", "api_key": "key"},
    {"source": "emby", "url": "", "api_key": "key"},
    {"source": "emby", "url": "http://emby.test", "api_key": ""},
])
@pytest.mark.asyncio
async def test_no_usable_media_server_is_said_without_asking_anyone(db_session, source):
    with media_server(source=source) as http, pytest.raises(MediaServerUnavailable) as refused:
        await authenticate_emby_user(db_session, "member-a", WRONG)

    assert refused.value.code == "media_server_not_configured"
    http.post.assert_not_awaited()


@pytest.mark.parametrize("error", [
    httpx.ConnectError("refused"),
    httpx.ConnectTimeout("slow"),
    httpx.ReadTimeout("slow"),
    httpx.RemoteProtocolError("cut"),
    httpx.InvalidURL("bad address"),
    NO_ASCII_KEY,
])
@pytest.mark.asyncio
async def test_no_answer_is_unreachable(db_session, error):
    with media_server(raises=error), pytest.raises(MediaServerUnavailable) as refused:
        await authenticate_emby_user(db_session, "member-a", WRONG)

    assert refused.value.code == "media_server_unreachable"


@pytest.mark.parametrize("status", [502, 503, 504])
@pytest.mark.asyncio
async def test_a_server_that_says_it_is_down_is_unreachable(db_session, status):
    with media_server(httpx.Response(status)), pytest.raises(MediaServerUnavailable) as refused:
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
    await add_member(db_session)

    with media_server(answer), pytest.raises(MediaServerUnavailable) as refused:
        await authenticate_emby_user(db_session, "member-a", WRONG)

    assert refused.value.code == "media_server_unreachable"


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500])
@pytest.mark.asyncio
async def test_any_other_status_reads_as_a_wrong_password(db_session, caplog, status):
    """A status nobody checked by hand must not open unlimited guessing."""
    with media_server(httpx.Response(status)), caplog.at_level(logging.WARNING, "mediakeeper.portal.emby_auth"):
        assert await authenticate_emby_user(db_session, "member-a", WRONG) is None

    assert any(f"HTTP {status}" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_a_media_server_down_costs_no_try(client, db_session):
    """Three tries during a breakdown block nobody, and the member gets in once it is back."""
    await add_member(db_session)

    with media_server(raises=httpx.ConnectError("refused")):
        answers = [await sign_in(client) for _ in range(3)]

    assert [(a.status_code, a.json()["detail"]) for a in answers] == [(503, "media_server_unreachable")] * 3
    assert await failures(db_session) == []
    assert (await db_session.execute(select(SecurityBlock))).scalars().all() == []

    with media_server(ACCEPTED):
        assert (await sign_in(client, password="any")).status_code == 200


@pytest.mark.asyncio
async def test_no_media_server_says_so_and_costs_no_try(client, db_session):
    with media_server(source=None):
        resp = await sign_in(client)

    assert (resp.status_code, resp.json()["detail"]) == (503, "media_server_not_configured")
    assert await failures(db_session) == []


@pytest.mark.parametrize("server", [
    {"raises": httpx.ConnectError("refused")},
    {"raises": NO_ASCII_KEY},
    {"source": None},
])
@pytest.mark.parametrize("name", ["admin", "ghost-admin"])
@pytest.mark.asyncio
async def test_an_admin_miss_still_counts_without_a_media_server(
    client, admin_user, db_session, monkeypatch, server, name,
):
    """The local password was checked and wrong: an install with no media server
    must not answer "no server" for a typo, nor let guesses go uncounted. A listed
    name with no account behaves the same."""
    monkeypatch.setenv("MK_ADMIN_USERS", "admin,ghost-admin")

    with media_server(**server):
        resp = await sign_in(client, name)

    assert (resp.status_code, resp.json()["detail"]) == (401, "invalid_credentials")
    assert await failures(db_session) == ["admin"]


@pytest.mark.asyncio
async def test_an_admin_right_password_needs_no_media_server(client, admin_user):
    with media_server(raises=httpx.ConnectError("refused")) as http:
        resp = await sign_in(client, "admin", ADMIN_PASSWORD)

    assert resp.status_code == 200
    http.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_an_imported_account_listed_as_admin_has_no_local_password_to_count(
    client, db_session, monkeypatch,
):
    monkeypatch.setenv("MK_ADMIN_USERS", "admin,member-a")
    await add_member(db_session)

    with media_server(raises=httpx.ConnectError("refused")):
        resp = await sign_in(client)

    assert (resp.status_code, resp.json()["detail"]) == (503, "media_server_unreachable")
    assert await failures(db_session) == []


@pytest.mark.asyncio
async def test_an_unexpected_status_counts_as_a_try(client, db_session):
    with media_server(httpx.Response(500)):
        resp = await sign_in(client)

    assert (resp.status_code, resp.json()["detail"]) == (401, "invalid_credentials")
    assert await failures(db_session) == ["portal"]
