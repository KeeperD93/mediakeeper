"""Display name rules across scripts: Greek capitals reached after NFKD, invisible
characters that would copy another member's name, joiners and emoji sequences that
shape real names, the minimum length (vowel signs, spaces, Chinese and Korean), and
names that contain a reserved word.

Special characters are written with chr() so the source shows each code point."""
from __future__ import annotations

import pytest

from services.portal.display_name_rules import (
    display_name_skeleton,
    is_reserved_display_name,
)
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

CHECK_URL = "/api/portal/profiles/me/check-username"
ME_URL = "/api/portal/profiles/me"

ZWNJ, ZWJ, STYLE = chr(0x200C), chr(0x200D), chr(0xFE0F)
RAINBOW_FLAG = chr(0x1F3F3) + STYLE + ZWJ + chr(0x1F308)
SCOTLAND_FLAG = chr(0x1F3F4) + "".join(chr(0xE0000 + ord(c)) for c in "gbsct") + chr(0xE007F)


async def _login(client, db_session, **kwargs):
    user, profile = await make_portal_user(db_session, **kwargs)
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    return user, profile


async def _verdict(client, name: str) -> str:
    return (await client.get(CHECK_URL, params={"name": name})).json()["reason"]


@pytest.mark.parametrize("name", [
    "AD" + chr(0x1D6B3) + "IN",  # mathematical bold capital Mu
    "ADMI" + chr(0x1D6B4),  # mathematical bold capital Nu
    "ROO" + chr(0x1D6BB),  # mathematical bold capital Tau
])
def test_greek_capitals_brought_out_by_nfkd_are_folded(name):
    assert is_reserved_display_name(name)


def test_accented_greek_capitals_keep_their_latin_reading():
    assert display_name_skeleton(chr(0x0389)) == "h"  # capital Eta with tonos
    assert display_name_skeleton(chr(0x03D2)) == "y"  # upsilon with hook


@pytest.mark.parametrize("name", [
    "Administrateur officiel",
    "Admin MediaKeeper",
    "AdminBob",
    "Administratrice",
    "Administrateur2",
    "Root Beer",
    "root42",
    chr(0x0410) + "dmin du soir",  # Cyrillic capital A
])
def test_a_reserved_word_inside_a_name_is_reserved(name):
    assert is_reserved_display_name(name)


@pytest.mark.parametrize("name", ["Badminton", "Groot", "Roots", "Rootkit", "Madmin"])
def test_names_that_only_share_letters_are_free(name):
    assert not is_reserved_display_name(name)


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    "Ali" + ZWJ + "ce",
    "Ali" + ZWNJ + "ce",
    "Alice" + STYLE,
    "Alice" + chr(0x180B),  # Mongolian variation selector
    "Alice" + chr(0x17B4),  # Khmer inherent vowel
    "Alice" + chr(0xE0100),  # variation selector 17
    "Alice" + chr(0xE0067),  # a tag outside a flag
    "Alice2" + STYLE,  # emoji style after a digit, outside a keycap
    "Alice" + chr(0x1D159) * 3,  # null noteheads, drawn empty
])
async def test_an_invisible_copy_of_a_member_name_is_invalid(client, db_session, name):
    await make_portal_user(db_session, username="bob", display_name="Alice")
    await _login(client, db_session, username="carol", display_name="Carol")
    assert await _verdict(client, name) == "invalid"


@pytest.mark.asyncio
async def test_a_reset_name_in_another_script_cannot_come_back_with_a_mark(client, db_session):
    sakura = chr(0x3055) + chr(0x304F) + chr(0x3089)
    await _login(
        client, db_session, username="alice", display_name=sakura,
        must_set=True, changed_days_ago=30,
    )
    assert await _verdict(client, sakura + chr(0x180B)) == "invalid"
    assert await _verdict(client, sakura) == "previous"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    chr(0x0DC1) + chr(0x0DCA) + ZWJ + chr(0x0DBB) + chr(0x0DD3),  # Sinhala, joiner after virama
    chr(0x0932) + chr(0x0915) + chr(0x094D) + ZWJ + chr(0x0937) + chr(0x094D) + chr(0x092E) + chr(0x0940),
    "Alice " + RAINBOW_FLAG,
    "Alice " + chr(0x1F3F3) + STYLE + ZWJ + chr(0x26A7) + STYLE,  # transgender flag
    "Alice " + chr(0x2764) + STYLE + ZWJ + chr(0x1F525),  # heart on fire
    "Alice " + chr(0x1F3C3) + chr(0x1F3FD) + ZWJ + chr(0x2640) + STYLE,  # runner, skin tone
    "Alice " + SCOTLAND_FLAG,
    "Alice " + "1" + STYLE + chr(0x20E3),  # keycap
])
async def test_joiners_and_emoji_sequences_of_real_names_are_free(client, db_session, name):
    await _login(client, db_session, username="carol", display_name="Carol")
    assert await _verdict(client, name) == "free"


@pytest.mark.asyncio
async def test_a_stored_name_with_a_rainbow_flag_stays_current(client, db_session):
    name = "Alice " + RAINBOW_FLAG
    await _login(client, db_session, username="alice", display_name=name, changed_days_ago=10)
    assert await _verdict(client, name) == "current"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    chr(0x0C30) + chr(0x0C35) + chr(0x0C3F),  # Ravi in Telugu
    chr(0x0917) + chr(0x0941) + chr(0x0930) + chr(0x0941),  # Guru in Hindi
    chr(0x0E2A) + chr(0x0E38) + chr(0x0E02),  # Suk in Thai
    chr(0x674E) + chr(0x5A1C),  # two Chinese ideographs
    chr(0xBBFC) + chr(0xC218),  # two Korean syllables
    chr(0x1106) + chr(0x1175) + chr(0x11AB) + chr(0x1109) + chr(0x116E),  # the same, decomposed
])
async def test_short_names_of_other_scripts_are_long_enough(client, db_session, name):
    await _login(client, db_session, username="carol", display_name="Carol")
    assert await _verdict(client, name) == "free"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    "A B",
    "A" + chr(0x200A) + "B",  # hair space
    chr(0x674E),  # one Chinese ideograph
    chr(0x3086) + chr(0x3044),  # two Japanese kana
    chr(0x0915) + chr(0x093F) * 5,  # one Devanagari letter under stacked vowel signs
])
async def test_spaces_and_stacked_signs_do_not_reach_the_minimum(client, db_session, name):
    await _login(client, db_session, username="carol", display_name="Carol")
    assert await _verdict(client, name) == "too_short"
