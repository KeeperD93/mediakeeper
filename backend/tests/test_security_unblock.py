"""Unblocking frees the person: the automatic blocks that refuse them go together,
and the failures behind them stop counting while staying listed."""
import logging
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.portal.profile import UserProfile
from services.security import FAIL_BLOCK_THRESHOLD, active_blocks, release_block
from tests._security_unblock_helpers import (
    AWAY,
    HOME,
    OTHER,
    add_attempt,
    add_block,
    fail,
    find_block,
    remaining_blocks,
    still_counting,
)

RIGHT = "Right-Synthetic-1!"
WRONG = "Wrong-Synthetic-1!"
# The test client's own address, the one every sign-in below is counted under.
CLIENT = "127.0.0.1"


@pytest.fixture
def member(make_user, db_session):
    """Member "member-a", whose media-server password is RIGHT, with the Emby check mocked."""
    sessions = {}

    async def _add():
        user = await make_user("member-a", role="viewer")
        profile = (await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )).scalar_one()
        sessions["member-a"] = {"token": "rq-member-a", "user": user, "profile": profile}

    async def _emby(db, username, password):
        return sessions.get(username.lower()) if password == RIGHT else None

    with patch("api.auth.login.authenticate_emby_user", new=AsyncMock(side_effect=_emby)), patch(
        "api.auth._portal.get_unread_news", new=AsyncMock(return_value=[]),
    ):
        yield _add


async def _sign_in(client, password: str) -> int:
    resp = await client.post("/api/auth/portal-login", json={"username": "member-a", "password": password})
    return resp.status_code


@pytest.mark.asyncio
async def test_unblock_then_the_right_password_gets_in(authed_client, member, db_session):
    client = authed_client
    await member()
    assert [await _sign_in(client, p) for p in (WRONG, WRONG, WRONG, RIGHT)] == [401, 401, 401, 429]

    block_id = await find_block(db_session, username="member-a")
    resp = await client.delete(f"/api/security/blocks/{block_id}")

    assert resp.status_code == 200
    assert resp.json()["linked_addresses"] == 1
    assert {(r["ip"], r["username"]) for r in resp.json()["removed"]} == {(None, "member-a"), (CLIENT, None)}
    assert await _sign_in(client, RIGHT) == 200


@pytest.mark.asyncio
async def test_unblock_then_one_typo_does_not_block_again(authed_client, member, db_session):
    client = authed_client
    await member()
    assert [await _sign_in(client, WRONG) for _ in range(3)] == [401, 401, 401]
    block_id = await find_block(db_session, username="member-a")
    assert (await client.delete(f"/api/security/blocks/{block_id}")).status_code == 200

    assert [await _sign_in(client, p) for p in (WRONG, RIGHT)] == [401, 200]
    assert await remaining_blocks(db_session) == set()


@pytest.mark.asyncio
async def test_an_unblocked_name_gets_exactly_three_new_tries(db_session):
    await fail(db_session, HOME, "member-a")
    await release_block(db_session, await find_block(db_session, username="member-a"))

    await fail(db_session, HOME, "member-a", times=FAIL_BLOCK_THRESHOLD - 1)
    assert await active_blocks(db_session, HOME, "member-a", "portal") == []

    await fail(db_session, HOME, "member-a", times=1)
    assert await remaining_blocks(db_session) == {(None, "member-a", "portal"), (HOME, None, "portal")}


@pytest.mark.asyncio
async def test_the_name_goes_from_every_address_but_only_blocked_ones_are_freed(db_session):
    """Failures of the name stop counting wherever they came from; another name's
    only where an address block was lifted."""
    await fail(db_session, HOME, "member-a", times=2)
    await fail(db_session, HOME, "member-b", times=1)
    await fail(db_session, AWAY, "member-a", times=1)
    await fail(db_session, AWAY, "member-c", times=1)

    released = await release_block(db_session, await find_block(db_session, username="member-a"))

    assert released["linked_addresses"] == 1
    assert await remaining_blocks(db_session) == set()
    assert await still_counting(db_session) == [(AWAY, "member-c")]


@pytest.mark.asyncio
async def test_another_names_block_stays_when_the_shared_address_is_freed(db_session):
    await fail(db_session, HOME, "member-b")
    await fail(db_session, HOME, "member-a")

    await release_block(db_session, await find_block(db_session, username="member-a"))

    assert await remaining_blocks(db_session) == {(None, "member-b", "portal")}
    assert await still_counting(db_session) == []


@pytest.mark.asyncio
async def test_unblocking_an_address_keeps_the_name_blocked(db_session):
    await fail(db_session, AWAY, "member-a", times=1)
    await fail(db_session, HOME, "member-a", times=2)
    await fail(db_session, HOME, "member-b", times=1)

    released = await release_block(db_session, await find_block(db_session, ip=HOME))

    assert released["linked_addresses"] == 0
    assert await remaining_blocks(db_session) == {(None, "member-a", "portal")}
    assert await active_blocks(db_session, HOME, "member-b", "portal") == []
    assert await active_blocks(db_session, OTHER, "member-a", "portal")
    assert await still_counting(db_session) == [(AWAY, "member-a")]


@pytest.mark.asyncio
async def test_duplicate_automatic_blocks_go_together(db_session):
    """Two simultaneous failures can each set a block: one left behind still refuses."""
    await add_attempt(db_session, HOME, "member-a")
    name_id = await add_block(db_session, username="member-a")
    await add_block(db_session, username="member-a")
    await add_block(db_session, ip=HOME)
    await add_block(db_session, ip=HOME)

    released = await release_block(db_session, name_id)

    assert len(released["removed"]) == 4
    assert released["linked_addresses"] == 1
    assert await remaining_blocks(db_session) == set()


@pytest.mark.asyncio
async def test_an_address_duplicate_is_not_a_linked_address(db_session):
    first = await add_block(db_session, ip=HOME)
    await add_block(db_session, ip=HOME)

    released = await release_block(db_session, first)

    assert len(released["removed"]) == 2
    assert released["linked_addresses"] == 0
    assert await remaining_blocks(db_session) == set()


@pytest.mark.asyncio
async def test_the_lists_say_what_was_neutralised_and_what_is_automatic(authed_client, admin_user, db_session, caplog):
    client = authed_client
    failures_url = "/api/security/attempts?only_failures=true"
    await fail(db_session, HOME, "member-a")
    await add_block(db_session, ip=OTHER, automatic=0)

    listed = (await client.get("/api/security/blocks")).json()["items"]
    assert {(b["ip"], b["automatic"]) for b in listed} == {(None, True), (HOME, True), (OTHER, False)}
    attempts = (await client.get(failures_url)).json()["items"]
    assert [a["cleared_at"] for a in attempts] == [None] * FAIL_BLOCK_THRESHOLD

    block_id = await find_block(db_session, username="member-a")
    with caplog.at_level(logging.INFO, logger="mediakeeper.api.security"):
        assert (await client.delete(f"/api/security/blocks/{block_id}")).status_code == 200

    # Nothing else keeps a trace of rows that are gone: who lifted what stays in the log.
    assert f"admin_id={admin_user.id}" in caplog.text
    assert HOME in caplog.text
    assert "member-a" in caplog.text
    assert "'scope': 'portal'" in caplog.text

    attempts = (await client.get(failures_url)).json()["items"]
    assert len(attempts) == FAIL_BLOCK_THRESHOLD
    assert all(a["cleared_at"] for a in attempts)
    assert {b["ip"] for b in (await client.get("/api/security/blocks")).json()["items"]} == {OTHER}

    gone = await client.delete(f"/api/security/blocks/{block_id}")
    assert gone.status_code == 404
    assert gone.json()["detail"] == "block_not_found"
