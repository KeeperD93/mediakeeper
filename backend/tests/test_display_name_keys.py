"""One display name per member: the comparison columns kept in step with the
name, « taken » on the key and the skeleton, admins and members who still owe a
name holding none, names shaped like a provisional pseudo refused, the race
closed by the unique key, and the provisional pseudo stored at provisioning.

Special characters are written with chr() so the source shows each code point."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from models.portal.profile import UserProfile
from models.user import User
from services.portal import admin_users, admin_users_actions
from services.portal import display_name_rules as rules
from services.portal._pseudo_words import generate_pseudo
from services.portal.profiles import get_or_create_profile
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

CHECK_URL = "/api/portal/profiles/me/check-username"
ME_URL = "/api/portal/profiles/me"


async def _login(client, db_session, **kwargs):
    user, profile = await make_portal_user(db_session, **kwargs)
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    return user, profile


async def _verdict(client, name: str) -> str:
    return (await client.get(CHECK_URL, params={"name": name})).json()["reason"]


@pytest.mark.asyncio
async def test_columns_follow_the_name_the_flag_and_the_role(db_session):
    _, member = await make_portal_user(db_session, username="bob", display_name=chr(0xC9) + "lodie")
    assert member.display_name_key == chr(0xE9) + "lodie"
    assert member.display_name_skeleton == rules.display_name_skeleton("Elodie")  # accent folded

    _, admin = await make_portal_user(db_session, username="olivia", display_name="OliviaOps", role="admin")
    _, newcomer = await make_portal_user(db_session, username="carol", must_set=True)
    assert (admin.display_name_key, admin.display_name_skeleton) == (None, None)
    assert (newcomer.display_name_key, newcomer.display_name_skeleton) == (None, None)

    member.display_name_must_set = True  # reset by an admin
    await db_session.commit()
    assert (member.display_name_key, member.display_name_skeleton) == (None, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(("stored", "candidate"), [
    (chr(0xC9) + "lodie", chr(0xE9) + "LODIE"),  # non-ASCII capital
    ("Zo" + chr(0xE9), "Zoe" + chr(0x0301)),  # decomposed form
    ("Alice", chr(0x0410) + "lice"),  # Cyrillic capital A
    ("Zoe", "Zo" + chr(0xE9)),  # same skeleton
    ("Nico", "N1co"),
])
async def test_a_name_another_member_shows_is_taken(client, db_session, stored, candidate):
    await make_portal_user(db_session, username="bob", display_name=stored)
    await _login(client, db_session, username="carol", display_name="Carol")
    assert await _verdict(client, candidate) == "taken"


@pytest.mark.asyncio
async def test_names_held_by_no_member_are_free(client, db_session):
    await make_portal_user(db_session, username="olivia", display_name="OliviaOps", role="admin")
    await make_portal_user(db_session, username="dave", display_name="DaveLogin", must_set=True)
    await _login(client, db_session, username="carol", display_name="Carol")
    assert await _verdict(client, "oliviaops") == "free"
    assert await _verdict(client, "DaveLogin") == "free"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    "Renard-Bleu-42",
    "renard bleu 7",
    "Golden-Owl-84",
    "Blue" + chr(0x2010) + "Fox" + chr(0x2010) + "99",
])
async def test_a_name_shaped_like_a_provisional_pseudo_is_refused(client, db_session, name):
    await _login(client, db_session, username="carol", display_name="Carol")
    assert await _verdict(client, name) == "generated"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["Renard", "Renard-Bleu", "Hibou-42", "Blue Fox Fan"])
async def test_names_that_only_use_its_words_stay_free(client, db_session, name):
    await _login(client, db_session, username="carol", display_name="Carol")
    assert await _verdict(client, name) == "free"


@pytest.mark.asyncio
async def test_a_member_who_kept_a_provisional_pseudo_must_change_it(client, db_session):
    user, profile = await _login(client, db_session, username="carol", display_name="Carol")
    profile.display_name = generate_pseudo(user.id, "fr")
    await db_session.commit()
    assert await _verdict(client, profile.display_name) == "generated"


@pytest.mark.asyncio
async def test_a_member_who_owes_a_name_is_not_locked(client, db_session):
    # Sent back to « must choose » ten days after a change: free to pick at once.
    await _login(client, db_session, username="carol", display_name="Carol", must_set=True, changed_days_ago=10)
    state = (await client.get("/api/portal/profiles/me/username-state")).json()
    assert (state["must_set"], state["locked"]) == (True, False)
    assert await _verdict(client, "Caroline") == "free"


@pytest.mark.asyncio
async def test_the_same_name_in_decomposed_form_stays_current(client, db_session):
    await _login(client, db_session, username="zoe", display_name="Zo" + chr(0xE9), changed_days_ago=10)
    assert await _verdict(client, "Zoe" + chr(0x0301)) == "current"


@pytest.mark.asyncio
async def test_the_unique_key_refuses_the_second_of_two_saves(client, db_session, monkeypatch):
    await make_portal_user(db_session, username="bob", display_name="Zed")
    await _login(client, db_session, username="carol", display_name="Carol")

    async def nobody(*_args, **_kwargs):  # both saves judged the name free
        return False

    monkeypatch.setattr(rules, "is_display_name_taken", nobody)
    resp = await client.put(ME_URL, json={"display_name": "zed"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "display_name_taken"
    assert (await client.get(ME_URL)).json()["display_name"] == "Carol"


@pytest.mark.asyncio
async def test_an_admin_rename_to_a_name_in_use_is_refused(db_session):
    await make_portal_user(db_session, username="bob", display_name="Zed")
    user, profile = await make_portal_user(db_session, username="carol", display_name="Carol")
    result = await admin_users.update_user_identity(db_session, profile, user, display_name="ZED")
    assert result == {"error": "display_name_taken"}
    await db_session.refresh(profile)
    assert profile.display_name == "Carol"


@pytest.mark.asyncio
async def test_the_unique_key_refuses_an_admin_rename_judged_free(db_session, monkeypatch):
    await make_portal_user(db_session, username="bob", display_name="Zed")
    user, profile = await make_portal_user(db_session, username="carol", display_name="Carol")

    async def nobody(*_args, **_kwargs):  # a member saved the name after the check
        return False

    monkeypatch.setattr(admin_users, "is_display_name_taken", nobody)
    result = await admin_users.update_user_identity(db_session, profile, user, display_name="zed")
    assert result == {"error": "display_name_taken"}
    await db_session.refresh(profile)
    assert profile.display_name == "Carol"


@pytest.mark.asyncio
@pytest.mark.parametrize(("login", "configured", "role"), [
    ("admin", "olivia", "viewer"),  # a sign-in name equal to « admin » is no admin
    ("olivia", "olivia", "admin"),
])
async def test_a_missing_profile_takes_the_admin_role_from_the_configuration(
    db_session, monkeypatch, login, configured, role,
):
    monkeypatch.setenv("MK_ADMIN_USERS", configured)
    user = User(username=login, hashed_password="x", is_active=True, must_change_password=False)
    db_session.add(user)
    await db_session.commit()

    profile = await get_or_create_profile(db_session, user)
    assert profile.role == role
    assert profile.display_name_must_set is (role != "admin")


@pytest.mark.asyncio
@pytest.mark.parametrize(("admin_name", "owes_a_name"), [
    ("zed", True),  # a member shows it: the unique key would refuse it
    ("Administrateur", True),  # reserved for admins
    ("Olivia", False),
])
async def test_a_former_admin_keeps_only_a_name_a_member_may_wear(db_session, admin_name, owes_a_name):
    await make_portal_user(db_session, username="bob", display_name="Zed")
    _, admin = await make_portal_user(db_session, username="olivia", display_name=admin_name, role="admin")

    result = await admin_users_actions.update_role(db_session, admin, role="viewer", admin_user_id=None)

    assert result == {"ok": True, "role": "viewer"}
    await db_session.refresh(admin)
    assert admin.display_name_must_set is owes_a_name
    assert admin.display_name_key == (None if owes_a_name else "olivia")


@pytest.mark.asyncio
async def test_a_missing_profile_is_created_under_its_provisional_pseudo(db_session):
    user = User(username="erin", hashed_password="x", is_active=True, must_change_password=False)
    db_session.add(user)
    await db_session.commit()

    profile = await get_or_create_profile(db_session, user)
    assert profile.display_name == generate_pseudo(user.id, "fr")
    assert profile.display_name_must_set is True
    stored = (await db_session.execute(
        select(UserProfile.display_name).where(UserProfile.user_id == user.id)
    )).scalar_one()
    assert stored != "erin"
