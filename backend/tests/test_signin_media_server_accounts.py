"""Which account a password accepted by the media server opens: found by the server's
own id first, under that account's blocks, and told apart only if it was ever let in."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy import select

from models.portal.profile import UserProfile
from services.portal.admin_users_actions import set_account_active
from services.portal.admin_users_expiration import _deactivate_one, expire_due_users
from services.portal.admin_users_lifecycle import soft_delete_user
from services.portal.emby_auth import AccountInactive, authenticate_emby_user
from services.portal.user_import import ensure_user_for_emby_session
from services.security import create_block
from tests._signin_media_server_helpers import (
    ACCEPTED,
    add_member,
    failures,
    media_server,
    sign_in,
)


async def _profile(db_session, user) -> UserProfile:
    return (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )).scalar_one()


@pytest.mark.asyncio
async def test_a_member_renamed_on_the_media_server_is_found_by_id(db_session):
    await add_member(db_session, "old-name", emby_id="emby-id-a")

    with media_server(ACCEPTED):
        session = await authenticate_emby_user(db_session, "new-name", "any")

    assert session["user"].username == "old-name"


@pytest.mark.asyncio
async def test_the_id_wins_over_a_name_that_belongs_to_someone_else(db_session):
    """A server account renamed like another member must not open that member's profile."""
    await add_member(db_session, "member-a", emby_id="emby-id-a")
    await add_member(db_session, "member-b", emby_id="emby-id-b")

    with media_server(ACCEPTED):
        session = await authenticate_emby_user(db_session, "member-b", "any")

    assert session["user"].username == "member-a"


@pytest.mark.asyncio
async def test_an_accented_capital_is_found_by_id(db_session):
    """The test database lower-cases only plain letters, so the name alone misses."""
    await add_member(db_session, "Émile", emby_id="emby-id-a")

    with media_server(ACCEPTED):
        session = await authenticate_emby_user(db_session, "Émile", "any")

    assert session["user"].username == "Émile"


@pytest.mark.asyncio
async def test_a_profile_without_an_id_is_found_by_name_and_gets_it(db_session):
    await add_member(db_session, "Member-A")

    with media_server(ACCEPTED):
        session = await authenticate_emby_user(db_session, "member-a", "any")

    assert session["profile"].emby_user_id == "emby-id-a"


@pytest.mark.parametrize("typed", ["member-b", "MEMBER-B"])
@pytest.mark.asyncio
async def test_two_profiles_on_one_id_the_name_typed_decides(db_session, typed):
    await add_member(db_session, "member-a", emby_id="emby-id-a")
    await add_member(db_session, "member-b", emby_id="emby-id-a")

    with media_server(ACCEPTED):
        session = await authenticate_emby_user(db_session, typed, "any")

    assert session["user"].username == "member-b"


@pytest.mark.asyncio
async def test_two_profiles_on_one_id_a_disabled_one_does_not_open_the_other(db_session):
    await add_member(db_session, "member-a", emby_id="emby-id-a")
    await add_member(db_session, "member-b", emby_id="emby-id-a", active=False, switched_off=True)

    with media_server(ACCEPTED), pytest.raises(AccountInactive):
        await authenticate_emby_user(db_session, "member-b", "any")


@pytest.mark.asyncio
async def test_two_profiles_on_one_id_any_other_name_opens_neither(db_session):
    await add_member(db_session, "member-a", emby_id="emby-id-a")
    await add_member(db_session, "member-b", emby_id="emby-id-a")

    with media_server(ACCEPTED):
        assert await authenticate_emby_user(db_session, "member-c", "any") is None


@pytest.mark.parametrize("scope", ["all", "portal", "admin"])
@pytest.mark.asyncio
async def test_a_name_block_follows_the_account(client, db_session, scope):
    """Blocked as "member-a", the account stays refused under its new server name."""
    await add_member(db_session, "member-a", emby_id="emby-id-a")
    await create_block(db_session, admin_id=None, ip=None, username="member-a", scope=scope, permanent=True)

    with media_server(ACCEPTED):
        resp = await sign_in(client, "new-name", "any")

    assert (resp.status_code, resp.json()["detail"]) == (429, "login_blocked")
    assert "rq_token" not in resp.cookies
    assert await failures(db_session) == []


@pytest.mark.asyncio
async def test_a_block_on_another_name_does_not_reach_the_account(client, db_session):
    await add_member(db_session, "member-a", emby_id="emby-id-a")
    await create_block(db_session, admin_id=None, ip=None, username="member-b", scope="all", permanent=True)

    with media_server(ACCEPTED):
        resp = await sign_in(client, "new-name", "any")

    assert resp.status_code == 200
    assert resp.json()["username"] == "member-a"


@pytest.mark.parametrize("flags", [{"active": False}, {"account_active": False}])
@pytest.mark.asyncio
async def test_a_switched_off_account_is_inactive(db_session, flags):
    await add_member(db_session, switched_off=True, **flags)

    with media_server(ACCEPTED), pytest.raises(AccountInactive):
        await authenticate_emby_user(db_session, "member-a", "any")


@pytest.mark.parametrize("switch_off", [
    lambda db, profile, user: set_account_active(db, profile, user, active=False, admin_user_id=None),
    lambda db, profile, user: soft_delete_user(db, profile, user, admin_user_id=None),
    lambda db, profile, user: _deactivate_one(db, profile, user, reason="test"),
])
@pytest.mark.asyncio
async def test_every_way_of_switching_an_account_off_tells_it_apart(db_session, switch_off):
    """They all stamp the date that separates it from an account never let in."""
    user = await add_member(db_session)
    await switch_off(db_session, await _profile(db_session, user), user)

    with media_server(ACCEPTED), pytest.raises(AccountInactive):
        await authenticate_emby_user(db_session, "member-a", "any")


@pytest.mark.asyncio
async def test_a_member_never_activated_reads_like_a_wrong_password(client, db_session):
    """Told apart, the page would confirm the password of anyone on the media server."""
    await add_member(db_session, account_active=False)

    with media_server(ACCEPTED):
        resp = await sign_in(client, password="any")

    assert (resp.status_code, resp.json()["detail"]) == (401, "invalid_credentials")
    assert await failures(db_session) == ["portal"]


@pytest.mark.asyncio
async def test_an_account_created_from_watching_reads_like_a_wrong_password(client, db_session):
    """The collector creates one for anyone who plays something on the media server."""
    await ensure_user_for_emby_session(db_session, emby_username="member-a", emby_user_id="emby-id-a")

    with media_server(ACCEPTED):
        resp = await sign_in(client, password="any")

    assert (resp.status_code, resp.json()["detail"]) == (401, "invalid_credentials")
    assert await failures(db_session) == ["portal"]


@pytest.mark.asyncio
async def test_a_switched_off_account_is_told_only_once_its_password_is_accepted(client, db_session):
    await add_member(db_session, active=False, switched_off=True)

    with media_server(httpx.Response(401)):
        wrong = await sign_in(client)
    assert (wrong.status_code, wrong.json()["detail"]) == (401, "invalid_credentials")
    assert await failures(db_session) == ["portal"]

    with media_server(ACCEPTED):
        right = await sign_in(client, password="any")
    assert (right.status_code, right.json()["detail"]) == (403, "account_disabled")
    assert await failures(db_session) == ["portal"]


@pytest.mark.asyncio
async def test_an_account_never_imported_reads_like_a_wrong_password(client, db_session):
    with media_server(ACCEPTED):
        resp = await sign_in(client, "never-imported", "any")

    assert (resp.status_code, resp.json()["detail"]) == (401, "invalid_credentials")
    assert await failures(db_session) == ["portal"]


@pytest.mark.asyncio
async def test_an_expired_account_is_inactive_and_switched_off(db_session):
    await add_member(db_session, access_end_date=datetime.now(timezone.utc) - timedelta(days=1))

    with media_server(ACCEPTED), pytest.raises(AccountInactive):
        await authenticate_emby_user(db_session, "member-a", "any")

    profile = (await db_session.execute(select(UserProfile))).scalar_one()
    await db_session.refresh(profile)
    assert profile.account_active is False


@pytest.mark.asyncio
async def test_an_expired_account_stays_refused_when_switching_it_off_fails(db_session):
    """The rollback expires every loaded row: reading one back must not turn the refusal into a 500."""
    await add_member(db_session, access_end_date=datetime.now(timezone.utc) - timedelta(days=1))

    with media_server(ACCEPTED), patch(
        "services.portal.admin_users_expiration._deactivate_one",
        new=AsyncMock(side_effect=RuntimeError("simulated commit failure")),
    ), pytest.raises(AccountInactive):
        await authenticate_emby_user(db_session, "member-a", "any")


@pytest.mark.asyncio
async def test_the_expiry_task_reports_a_failure_and_goes_on(db_session):
    past = datetime.now(timezone.utc) - timedelta(days=1)
    first = await add_member(db_session, "member-a", access_end_date=past)
    second = await add_member(db_session, "member-b", access_end_date=past)
    first_id, second_id = first.id, second.id

    with patch(
        "services.portal.admin_users_expiration._deactivate_one",
        new=AsyncMock(side_effect=RuntimeError("simulated commit failure")),
    ):
        result = await expire_due_users(db_session)

    assert result["processed"] == 0
    assert {error["user_id"] for error in result["errors"]} == {first_id, second_id}
