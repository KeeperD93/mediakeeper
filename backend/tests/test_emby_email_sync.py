"""Emby Connect email is mirrored onto the MediaKeeper profile (#113).

Covers the three capture points: selective import, login backfill, and the
bulk reconciliation pass. The extractor is unit-tested in isolation because
Emby exposes no dedicated email field — the value only exists as
``ConnectUserName`` on Emby-Connect-linked accounts, and may legitimately
hold a non-email username we must reject.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
from models.portal.profile import UserProfile
from models.user import User
from services.emby.users import email_from_emby_user


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"ConnectUserName": "alice@example.com"}, "alice@example.com"),
        ({"ConnectUserName": "  bob@mail.co  "}, "bob@mail.co"),
        ({"ConnectUserName": "legacy-connect-name"}, None),  # plain username, not an email
        ({"ConnectUserName": ""}, None),
        ({}, None),                                          # field absent (local Emby user)
        ({"ConnectUserName": "no@domain"}, None),            # domain has no dot
        ({"ConnectUserName": "two@@at.com"}, None),
        ({"ConnectUserName": "a b@spaced.com"}, None),
    ],
)
def test_email_from_emby_user(payload, expected):
    assert email_from_emby_user(payload) == expected


async def _seed_emby_profile(db_session, *, username, email=None):
    user = User(
        username=username,
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        account_active=True,
        source="emby",
        email=email,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


async def _run_login(db_session, username, emby_user):
    """Drive ``authenticate_emby_user`` with a stubbed Emby HTTP round-trip."""
    fake_response = AsyncMock()
    fake_response.status_code = 200
    fake_response.json = lambda: {"User": emby_user}
    fake_client = AsyncMock()
    fake_client.post = AsyncMock(return_value=fake_response)
    with patch(
        "services.portal.emby_auth.get_active_media_source",
        new=AsyncMock(return_value={
            "source": "emby", "url": "http://fake-emby.local", "api_key": "k",
        }),
    ), patch(
        "services.portal.emby_auth.get_internal_client",
        return_value=fake_client,
    ):
        from services.portal.emby_auth import authenticate_emby_user
        return await authenticate_emby_user(db_session, username, "pw")


@pytest.mark.asyncio
async def test_import_captures_connect_email(db_session):
    from services.portal.admin_users_emby import import_selected_emby_users

    emby_users = [
        {"Id": "guid-a", "Name": "alice", "ConnectUserName": "alice@example.com"},
        {"Id": "guid-b", "Name": "bob", "ConnectUserName": "bob-connect"},  # not an email
    ]
    with patch(
        "services.portal.admin_users_emby.list_emby_users",
        new=AsyncMock(return_value=emby_users),
    ):
        res = await import_selected_emby_users(
            db_session, emby_user_ids=["guid-a", "guid-b"], admin_user_id=None,
        )
    assert res.get("ok")

    alice = (await db_session.execute(
        select(UserProfile).where(UserProfile.emby_user_id == "guid-a")
    )).scalar_one()
    bob = (await db_session.execute(
        select(UserProfile).where(UserProfile.emby_user_id == "guid-b")
    )).scalar_one()
    assert alice.email == "alice@example.com"
    assert bob.email is None


@pytest.mark.asyncio
async def test_login_backfills_email_when_empty(db_session):
    _user, profile = await _seed_emby_profile(db_session, username="Carol")

    res = await _run_login(
        db_session, "carol", {"Id": "guid-c", "ConnectUserName": "carol@mail.io"},
    )
    assert res is not None
    await db_session.refresh(profile)
    assert profile.email == "carol@mail.io"


@pytest.mark.asyncio
async def test_login_does_not_clobber_existing_email(db_session):
    _user, profile = await _seed_emby_profile(
        db_session, username="Dave", email="typed@admin.set",
    )

    await _run_login(
        db_session, "dave", {"Id": "guid-d", "ConnectUserName": "other@mail.io"},
    )
    await db_session.refresh(profile)
    assert profile.email == "typed@admin.set"


@pytest.mark.asyncio
async def test_backfill_pass_fills_email(db_session):
    from services.portal.admin_users_emby import backfill_emby_user_ids

    _user, profile = await _seed_emby_profile(db_session, username="Erin")

    emby_users = [{
        "Id": "guid-e", "Name": "Erin", "ConnectUserName": "erin@mail.net",
        "Policy": {"IsDisabled": False},
    }]
    with patch(
        "services.portal.admin_users_emby.list_emby_users",
        new=AsyncMock(return_value=emby_users),
    ):
        res = await backfill_emby_user_ids(db_session)
    assert res.get("ok")
    assert res.get("emails_synced") == 1
    await db_session.refresh(profile)
    assert profile.email == "erin@mail.net"
    assert profile.emby_user_id == "guid-e"
