"""Display name rules shared by the live check and the save: look-alikes of the
reserved names, the placeholder and the reset name that cannot be confirmed, the
minimum length, and the reserved check that runs before « same as now »."""
from __future__ import annotations

import pytest

from services.portal._pseudo_words import generate_pseudo
from services.portal.display_name_rules import display_name_skeleton, is_reserved_display_name
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

CHECK_URL = "/api/portal/profiles/me/check-username"
ME_URL = "/api/portal/profiles/me"


# ─────────────────────────────────────────────────────────────────────────
# Look-alikes of a reserved name
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", [
    "Аdministrateur",  # Cyrillic capital A
    "Αdmin",  # Greek capital Alpha
    "аdmin",  # Cyrillic small a
    "Ad͏min",  # combining grapheme joiner
    "Admin️",  # variation selector
    "Adminㅤ",  # Hangul filler
    "Admin⠀",  # Braille blank
    "ADMİN",  # Turkish dotted capital I
    "ａｄｍｉｎ",  # full-width letters
    "Ad-min",
    "R O O T",
    "Administrаteur",  # Cyrillic a inside
])
def test_look_alikes_of_a_reserved_name_are_reserved(name):
    assert is_reserved_display_name(name)


@pytest.mark.parametrize("name", ["Administrateur2", "Rootkit", "Alice", "Bob"])
def test_other_names_are_not_reserved(name):
    assert not is_reserved_display_name(name)


def test_skeleton_keeps_only_latin_letters_and_digits():
    assert display_name_skeleton("Écureuil-Doré-42") == "ecureuildore42"
    assert display_name_skeleton("") == ""


async def _login(client, db_session, **kwargs):
    user, profile = await make_portal_user(db_session, **kwargs)
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    return user, profile


@pytest.mark.asyncio
async def test_check_and_save_refuse_a_look_alike(client, db_session):
    await _login(client, db_session, username="alice", display_name="Alice")
    body = (await client.get(CHECK_URL, params={"name": "Аdmin"})).json()
    assert (body["available"], body["reason"]) == (False, "reserved")

    resp = await client.put(ME_URL, json={"display_name": "Аdmin"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "display_name_reserved"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["‮nimda", "Ali​ce"])
async def test_invisible_or_direction_characters_are_invalid(client, db_session, name):
    await _login(client, db_session, username="alice", display_name="Alice")
    body = (await client.get(CHECK_URL, params={"name": name})).json()
    assert (body["available"], body["reason"]) == (False, "invalid")

    resp = await client.put(ME_URL, json={"display_name": name})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "display_name_invalid"


# ─────────────────────────────────────────────────────────────────────────
# Names a member who still owes one cannot confirm
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_new_account_cannot_keep_its_placeholder(client, db_session):
    # As provisioning stores it: the generated name, no change date yet.
    user, profile = await _login(client, db_session, username="alice", must_set=True)
    placeholder = generate_pseudo(user.id, "fr")
    profile.display_name = placeholder
    await db_session.commit()

    body = (await client.get(CHECK_URL, params={"name": placeholder.lower()})).json()
    assert (body["available"], body["reason"]) == (False, "generated")
    resp = await client.put(ME_URL, json={"display_name": placeholder})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "display_name_generated"
    me = (await client.get(ME_URL)).json()
    assert me["display_name_must_set"] is True


@pytest.mark.asyncio
async def test_english_placeholder_is_refused_too(client, db_session):
    user, _ = await _login(client, db_session, username="alice", display_name="Alice", must_set=True)
    body = (await client.get(CHECK_URL, params={"name": generate_pseudo(user.id, "en")})).json()
    assert (body["available"], body["reason"]) == (False, "generated")


@pytest.mark.asyncio
async def test_reset_member_cannot_keep_the_name_the_admin_reset(client, db_session):
    await _login(
        client, db_session, username="alice", display_name="Alice_42",
        must_set=True, changed_days_ago=30,
    )
    body = (await client.get(CHECK_URL, params={"name": "alice_42"})).json()
    assert (body["available"], body["reason"]) == (False, "previous")
    resp = await client.put(ME_URL, json={"display_name": "Alice_42"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "display_name_previous"

    resp = await client.put(ME_URL, json={"display_name": "Alice_43"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["display_name_must_set"] is False


# ─────────────────────────────────────────────────────────────────────────
# Reserved before « same as now », minimum length
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stored_reserved_name_cannot_be_kept_by_a_member(client, db_session):
    await _login(client, db_session, username="alice", display_name="Administrateur")
    body = (await client.get(CHECK_URL, params={"name": "administrateur"})).json()
    assert (body["available"], body["reason"]) == (False, "reserved")
    resp = await client.put(ME_URL, json={"display_name": "Administrateur"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "display_name_reserved"


@pytest.mark.asyncio
async def test_admin_keeps_a_reserved_name_whatever_the_flag(client, db_session):
    await _login(
        client, db_session, username="admin", display_name="admin", role="admin", must_set=True,
    )
    body = (await client.get(CHECK_URL, params={"name": "admin"})).json()
    assert (body["available"], body["reason"]) == (True, "current")
    resp = await client.put(ME_URL, json={"display_name": "admin"})
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_a_new_name_needs_three_characters(client, db_session):
    await _login(client, db_session, username="alice", display_name="Alice")
    body = (await client.get(CHECK_URL, params={"name": "Al"})).json()
    assert (body["available"], body["reason"]) == (False, "too_short")
    resp = await client.put(ME_URL, json={"display_name": "Al"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "display_name_too_short"


@pytest.mark.asyncio
async def test_a_short_name_already_chosen_stays_current(client, db_session):
    await _login(client, db_session, username="alice", display_name="Al", changed_days_ago=10)
    body = (await client.get(CHECK_URL, params={"name": "al"})).json()
    assert (body["available"], body["reason"]) == (True, "current")
