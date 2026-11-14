"""Display name rules shared by the live check and the save: look-alikes of the
reserved names, the placeholder and the reset name that cannot be confirmed, the
minimum length, and the reserved check that runs before « same as now ».

Look-alike and invisible characters are spelled as escapes, never as themselves."""
from __future__ import annotations

import pytest

from services.portal._pseudo_words import generate_pseudo
from services.portal.display_name_rules import (
    display_name_skeleton,
    is_reserved_display_name,
)
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

CHECK_URL = "/api/portal/profiles/me/check-username"
ME_URL = "/api/portal/profiles/me"


@pytest.mark.parametrize("name", [
    "\u0410dministrateur",  # Cyrillic capital A
    "\u0391dmin",  # Greek capital Alpha
    "\u0430dmin",  # Cyrillic small a
    "Ad\u034fmin",  # combining grapheme joiner
    "Admin\ufe0f",  # variation selector
    "Admin\u3164",  # Hangul filler
    "Admin\u2800",  # Braille blank
    "ADM\u0130N",  # Turkish dotted capital I
    "\uff41\uff44\uff4d\uff49\uff4e",  # full-width letters
    "Ad-min",
    "R O O T",
    "Administr\u0430teur",  # Cyrillic a inside
    "ADMlN",  # small L for capital I
    "adrnin",  # r and n for m
    "R00T",  # zeros for O
])
def test_look_alikes_of_a_reserved_name_are_reserved(name):
    assert is_reserved_display_name(name)


@pytest.mark.parametrize("name", ["Rootkit", "Alice", "Bob"])
def test_other_names_are_not_reserved(name):
    assert not is_reserved_display_name(name)


def test_skeleton_folds_to_latin_letters_and_digits():
    # l reads as i once case is gone, as I and 1 do.
    assert display_name_skeleton("\u00c9cureuil-Dor\u00e9-42") == "ecureuiidore42"
    assert display_name_skeleton("") == ""


async def _login(client, db_session, **kwargs):
    user, profile = await make_portal_user(db_session, **kwargs)
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    return user, profile


@pytest.mark.asyncio
async def test_check_and_save_refuse_a_look_alike(client, db_session):
    await _login(client, db_session, username="alice", display_name="Alice")
    body = (await client.get(CHECK_URL, params={"name": "\u0410dmin"})).json()
    assert (body["available"], body["reason"]) == (False, "reserved")

    resp = await client.put(ME_URL, json={"display_name": "\u0410dmin"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "display_name_reserved"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    "\u202enimda",  # right-to-left override
    "Ali\u200bce",  # zero-width space
])
async def test_invisible_or_direction_characters_are_invalid(client, db_session, name):
    await _login(client, db_session, username="alice", display_name="Alice")
    body = (await client.get(CHECK_URL, params={"name": name})).json()
    assert (body["available"], body["reason"]) == (False, "invalid")

    resp = await client.put(ME_URL, json={"display_name": name})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "display_name_invalid"


# Names a member who still owes one cannot confirm.


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


# Reserved before « same as now », minimum length.


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


# Bypasses found by the adversarial review, written with chr() so the source
# shows which code point each case uses.


@pytest.mark.parametrize("name", [
    "ADM" + chr(0x04C0) + "N",  # capital palochka, folded to the small one in the table
    chr(0x1D6A8) + "DMIN",  # mathematical bold capital Alpha
    chr(0x03AC) + "dmin",  # Greek alpha with tonos, decomposed before the table
])
def test_look_alikes_reached_after_normalisation_are_reserved(name):
    assert is_reserved_display_name(name)


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    chr(0x3164) * 3,  # Hangul fillers only
    chr(0x2800) * 3,  # Braille blanks only
    "Alice" + chr(0x034F),  # grapheme joiner after a name
    "Bob" + chr(0x0007) + "by",  # control character
    chr(0x200D) + "Alice",  # joiner at an edge
    "!!!",  # nothing to read
])
async def test_blank_or_hidden_names_are_invalid(client, db_session, name):
    await _login(client, db_session, username="carol", display_name="Carol")
    body = (await client.get(CHECK_URL, params={"name": name})).json()
    assert (body["available"], body["reason"]) == (False, "invalid")


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    chr(0x0639) + chr(0x0644) + chr(0x06CC) + chr(0x200C) + chr(0x0631) + chr(0x0636) + chr(0x0627),
    "Dev " + chr(0x1F469) + chr(0x200D) + chr(0x1F4BB),
    chr(0x3086) + chr(0x304D) + chr(0x306A),  # three Japanese letters
])
async def test_joiners_between_letters_stay_allowed(client, db_session, name):
    await _login(client, db_session, username="carol", display_name="Carol")
    body = (await client.get(CHECK_URL, params={"name": name})).json()
    assert (body["available"], body["reason"]) == (True, "free")


@pytest.mark.asyncio
async def test_combining_marks_do_not_count_toward_the_minimum(client, db_session):
    await _login(client, db_session, username="carol", display_name="Carol")
    body = (await client.get(CHECK_URL, params={"name": "A" + chr(0x0300) * 2})).json()
    assert body["reason"] == "too_short"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    chr(0x0410) + "lice_42",  # Cyrillic capital A
    "Alice-42",  # another separator
    "Alice_42" + chr(0x200B),  # zero-width space: refused as invalid first
])
async def test_reset_name_cannot_come_back_as_a_look_alike(client, db_session, name):
    await _login(
        client, db_session, username="alice", display_name="Alice_42",
        must_set=True, changed_days_ago=30,
    )
    body = (await client.get(CHECK_URL, params={"name": name})).json()
    assert body["available"] is False
    assert body["reason"] in ("previous", "invalid")


@pytest.mark.asyncio
async def test_placeholder_cannot_come_back_with_another_hyphen(client, db_session):
    user, profile = await _login(client, db_session, username="alice", must_set=True)
    profile.display_name = generate_pseudo(user.id, "fr")
    await db_session.commit()
    look_alike = profile.display_name.replace("-", chr(0x2010))
    body = (await client.get(CHECK_URL, params={"name": look_alike})).json()
    assert (body["available"], body["reason"]) == (False, "generated")


@pytest.mark.asyncio
async def test_byte_order_marks_at_the_edges_are_trimmed_by_both_routes(client, db_session):
    await _login(client, db_session, username="carol", display_name="Carol")
    name = chr(0xFEFF) + "Bobby" + chr(0xFEFF)
    body = (await client.get(CHECK_URL, params={"name": name})).json()
    assert (body["available"], body["reason"]) == (True, "free")
    resp = await client.put(ME_URL, json={"display_name": name})
    assert resp.status_code == 200, resp.text
    assert resp.json()["display_name"] == "Bobby"


@pytest.mark.asyncio
async def test_a_null_name_is_ignored_not_a_server_error(client, db_session):
    await _login(client, db_session, username="carol", display_name="Carol")
    resp = await client.put(ME_URL, json={"display_name": None, "bio": "hi"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["display_name"] == "Carol"
