"""Rules a display name must pass when a member picks one.

The live check, the profile update and the first-login wizard all ask
``judge_display_name``: a name the check accepts is a name the save accepts.
"""
import re
import unicodedata
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants import display_name as dn
from models.portal.profile import UserProfile
from services.portal import strip_tags_and_trim
from services.portal._pseudo_words import generate_pseudo
from services.portal.admin_users_constants import ROLE_ADMIN
from services.portal.profile_serializers import display_name_locked_until

# Only the admin role may wear these, or anything that reads like them.
RESERVED_DISPLAY_NAMES = frozenset({
    "admin", "administrator", "administrateur", "root",
})

# Letters of other scripts drawn like a Latin one, by code point. NFKD then folds
# accents, full-width and ligature forms; case and the rest are dropped after.
_LOOKALIKES = str.maketrans({
    # Cyrillic capitals: A B E K M H O P C T Y X I J S
    0x0410: "a", 0x0412: "b", 0x0415: "e", 0x041A: "k", 0x041C: "m",
    0x041D: "h", 0x041E: "o", 0x0420: "p", 0x0421: "c", 0x0422: "t",
    0x0423: "y", 0x0425: "x", 0x0406: "i", 0x0408: "j", 0x0405: "s",
    # Cyrillic small: a b e k m h o p c t y x i j s d h q w l
    0x0430: "a", 0x0432: "b", 0x0435: "e", 0x043A: "k", 0x043C: "m",
    0x043D: "h", 0x043E: "o", 0x0440: "p", 0x0441: "c", 0x0442: "t",
    0x0443: "y", 0x0445: "x", 0x0456: "i", 0x0458: "j", 0x0455: "s",
    0x0501: "d", 0x04BB: "h", 0x051B: "q", 0x051D: "w", 0x04CF: "l",
    # Greek capitals: A B E Z H I K M N O P T Y X
    0x0391: "a", 0x0392: "b", 0x0395: "e", 0x0396: "z", 0x0397: "h",
    0x0399: "i", 0x039A: "k", 0x039C: "m", 0x039D: "n", 0x039F: "o",
    0x03A1: "p", 0x03A4: "t", 0x03A5: "y", 0x03A7: "x",
    # Greek small: a i k v o p u x
    0x03B1: "a", 0x03B9: "i", 0x03BA: "k", 0x03BD: "v", 0x03BF: "o",
    0x03C1: "p", 0x03C5: "u", 0x03C7: "x",
    # Latin dotless i, alpha and script g
    0x0131: "i", 0x0251: "a", 0x0261: "g",
})
_SAME_SHAPE = str.maketrans({"l": "i", "1": "i", "0": "o"})


def display_name_skeleton(name: str) -> str:
    """What a name reads as: look-alike letters, accents, width, case, invisible
    characters and punctuation folded away, only ``a-z`` and ``0-9`` kept. The
    table runs before NFKD, between NFKD and casefold (the capitals NFKD brings out
    of mathematical or accented letters are still capitals there), and after
    casefold (decomposed letters such as Cyrillic yi, the capital palochka)."""
    folded = unicodedata.normalize("NFKD", (name or "").translate(_LOOKALIKES))
    folded = folded.translate(_LOOKALIKES).casefold().translate(_LOOKALIKES)
    kept = "".join(ch for ch in folded if "a" <= ch <= "z" or "0" <= ch <= "9")
    # Latin shapes a reader mixes up: I, l and 1 (once casefolded: i, l, 1), O and 0,
    # « rn » and « m ».
    return kept.replace("rn", "m").translate(_SAME_SHAPE)


_RESERVED_SKELETONS = frozenset(display_name_skeleton(n) for n in RESERVED_DISPLAY_NAMES)
# Every admin title starts with « admin » (administrator, administratrice…): a word
# that does is reserved. « root » only as a whole word, so « Roots » stays free.
_RESERVED_PREFIX = display_name_skeleton("admin")


def _words(name: str) -> list[str]:
    """Runs of letters, digits and marks, also cut where a small letter meets a
    capital (« AdminBob »)."""
    words: list[str] = []
    current = ""
    for ch in name:
        if unicodedata.category(ch)[0] not in "LNM":
            if current:
                words.append(current)
            current = ""
            continue
        if current and current[-1].islower() and ch.isupper():
            words.append(current)
            current = ""
        current += ch
    if current:
        words.append(current)
    return words


def is_reserved_display_name(name: str) -> bool:
    """A reserved name or a look-alike of one, alone or as a word of the name
    (« Admin MediaKeeper », « root42 »)."""
    if display_name_skeleton(name) in _RESERVED_SKELETONS:
        return True
    for word in _words(name):
        # 0 and 1 already read as o and i; other digits only pad the word.
        skeleton = display_name_skeleton(word).strip("23456789")
        if skeleton in _RESERVED_SKELETONS or skeleton.startswith(_RESERVED_PREFIX):
            return True
    return False


# Blank fillers with no ink of their own (the null notehead is drawn empty): a name
# could hide behind them.
_BLANKS = frozenset({0x034F, 0x115F, 0x1160, 0x2800, 0x3164, 0xFFA0, 0x1D159})
# Default_Ignorable marks (variation selectors, Mongolian and Khmer ones), drawn as
# nothing; format characters (Cf) are ignorable too.
_IGNORABLE_MARKS = ((0x17B4, 0x17B5), (0x180B, 0x180F), (0xFE00, 0xFE0F), (0xE0100, 0xE01EF))
_ZWNJ, _ZWJ, _EMOJI_STYLE = 0x200C, 0x200D, 0xFE0F
_KEYCAP = chr(0x20E3)
_VIRAMA_CLASS = 9
_SKIN_TONES = range(0x1F3FB, 0x1F400)
# A subdivision flag (Scotland, England, Wales): black flag, tag letters, cancel tag.
_TAG_FLAG = re.compile(
    chr(0x1F3F4) + "[" + chr(0xE0020) + "-" + chr(0xE007E) + "]+" + chr(0xE007F)
)
# Chinese ideographs and Korean syllables: each character is a whole syllable.
_SYLLABIC = ("CJK UNIFIED IDEOGRAPH", "CJK COMPATIBILITY IDEOGRAPH", "HANGUL SYLLABLE")
# Scripts that write vowels as letters, so their accents do not count as characters.
_LETTER_VOWEL_SCRIPTS = ("LATIN", "GREEK", "CYRILLIC")
_EDGES = re.compile(r"^[\s﻿]+|[\s﻿]+$")


def clean_display_name(raw: str | None) -> str:
    """A submitted name as it is judged and stored: tags stripped, clipped, and
    trimmed of spaces and byte-order marks, as the browser trims it."""
    return _EDGES.sub("", strip_tags_and_trim(raw, max_len=dn.MAX_LENGTH))


def _visible(ch: str) -> bool:
    return unicodedata.category(ch) not in ("Mn", "Me", "Cf") and ord(ch) not in _BLANKS


def _ignorable(ch: str) -> bool:
    cp = ord(ch)
    return unicodedata.category(ch) == "Cf" or any(lo <= cp <= hi for lo, hi in _IGNORABLE_MARKS)


def _emoji_ends_at(name: str, i: int) -> bool:
    """An emoji (So or Sk) ends at ``i``, past its style selector and skin tone."""
    while i >= 0 and (ord(name[i]) == _EMOJI_STYLE or ord(name[i]) in _SKIN_TONES):
        i -= 1
    return i >= 0 and unicodedata.category(name[i]) in ("So", "Sk")


def _shapes_text(name: str, i: int) -> bool:
    """An invisible character at ``i`` that changes the drawing: a joiner after a
    virama (RFC 5892, Indic half-forms), ZWNJ between two Arabic letters, ZWJ
    between two emoji, and the emoji style selector after an emoji or a keycap."""
    cp = ord(name[i])
    before = name[i - 1] if i else ""
    after = name[i + 1] if i + 1 < len(name) else ""
    if cp == _EMOJI_STYLE:
        keycap = bool(before) and before in "0123456789#*" and after == _KEYCAP
        return keycap or (bool(before) and _emoji_ends_at(name, i - 1))
    if cp not in (_ZWNJ, _ZWJ) or not before:
        return False
    if unicodedata.combining(before) == _VIRAMA_CLASS:
        return True
    if not after:
        return False
    if cp == _ZWNJ:
        return unicodedata.bidirectional(before) == unicodedata.bidirectional(after) == "AL"
    return _emoji_ends_at(name, i - 1) and unicodedata.category(after) in ("So", "Sk")


def _hides_text(name: str) -> bool:
    """Characters that can make a name blank or show it as another one: controls,
    private-use and unassigned code points, line breaks, blank fillers, and every
    character Unicode draws as nothing (format characters, variation selectors),
    save where ``_shapes_text`` finds it shapes the text and in a subdivision flag."""
    flag_tags = {i for m in _TAG_FLAG.finditer(name) for i in range(m.start() + 1, m.end())}
    for i, ch in enumerate(name):
        if unicodedata.category(ch) in ("Cc", "Co", "Cn", "Zl", "Zp") or ord(ch) in _BLANKS:
            return True
        if _ignorable(ch) and i not in flag_tags and not _shapes_text(name, i):
            return True
    return False


def _has_ink(name: str) -> bool:
    """At least one letter, digit or symbol to see."""
    return any(unicodedata.category(ch)[0] in "LNS" for ch in name if _visible(ch))


def _visible_length(name: str) -> int:
    """Characters a reader counts: letters, digits and symbols, plus one vowel sign
    per letter of a script that writes vowels as marks (Indic, Thai). Spaces,
    punctuation, invisible characters and stacked accents do not count."""
    count, base, marked = 0, "", False
    for ch in unicodedata.normalize("NFC", name):
        category = unicodedata.category(ch)
        if category[0] in "LNS" and _visible(ch):
            count, base, marked = count + 1, ch, False
        elif category in ("Mn", "Mc"):
            if not marked and _counts_its_marks(base) and not _ignorable(ch):
                count, marked = count + 1, True
        else:
            base = ""
    return count


def _counts_its_marks(base: str) -> bool:
    return (
        bool(base) and unicodedata.category(base)[0] == "L"
        and not unicodedata.name(base, "").startswith(_LETTER_VOWEL_SCRIPTS)
    )


def _min_length(name: str) -> int:
    """Two characters for a name written in Chinese ideographs or Korean
    syllables, three otherwise."""
    composed = unicodedata.normalize("NFC", name)
    letters = [ch for ch in composed if unicodedata.category(ch)[0] == "L"]
    if letters and all(unicodedata.name(ch, "").startswith(_SYLLABIC) for ch in letters):
        return dn.MIN_LENGTH_SYLLABIC
    return dn.MIN_LENGTH


def _fold(name: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKC", name).casefold()
        if not _ignorable(ch) and ord(ch) not in _BLANKS
    )


def _same_name(a: str, b: str) -> bool:
    """The same name to the eye: equal once folded, or equal non-empty skeletons."""
    skeleton = display_name_skeleton(a)
    return _fold(a) == _fold(b) or (bool(skeleton) and skeleton == display_name_skeleton(b))


def is_display_name_locked(profile: UserProfile) -> bool:
    until = display_name_locked_until(profile)
    return bool(until and until > datetime.now(UTC))


async def is_display_name_taken(
    db: AsyncSession, candidate: str, *, exclude_user_id: int | None = None,
) -> bool:
    """Case-insensitive existence check, optionally ignoring one user.

    Unlocked read: callers tolerate the check-then-insert race — uniqueness
    is best-effort (see ``resolve_unique_display_name``).
    """
    if not candidate:
        return False
    stmt = select(UserProfile.user_id).where(
        func.lower(UserProfile.display_name) == candidate.lower()
    )
    if exclude_user_id is not None:
        stmt = stmt.where(UserProfile.user_id != exclude_user_id)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def judge_display_name(
    db: AsyncSession,
    profile: UserProfile,
    name: str,
    *,
    admin_override: bool = False,
) -> str:
    """Verdict on ``name`` (as ``clean_display_name`` returns it) for ``profile``:
    ``current`` or ``free`` when it may be kept or taken, else the refusal.

    A member who still owes a name (first login, or reset by an admin) cannot
    confirm the stored one, nor anything that looks like it: it is the random
    placeholder or the name the admin reset. The reserved check runs before
    « same as now », so a reserved name stored by an older path cannot be kept.
    """
    if not name or _hides_text(name) or not _has_ink(name):
        return dn.INVALID
    is_admin = profile.role == ROLE_ADMIN
    # An admin never owes a public name: the flag is masked for them everywhere.
    must_set = bool(profile.display_name_must_set) and not is_admin
    stored = profile.display_name or ""
    if must_set:
        if _same_name(name, stored):
            return dn.PREVIOUS if profile.display_name_changed_at else dn.GENERATED
        if any(_same_name(name, generate_pseudo(profile.user_id, lang)) for lang in ("fr", "en")):
            return dn.GENERATED
    if not is_admin and is_reserved_display_name(name):
        return dn.RESERVED
    if name.lower() == stored.lower():
        return dn.CURRENT
    if _visible_length(name) < _min_length(name):
        return dn.TOO_SHORT
    if not admin_override and not must_set and is_display_name_locked(profile):
        return dn.LOCKED
    if await is_display_name_taken(db, name, exclude_user_id=profile.user_id):
        return dn.TAKEN
    return dn.FREE
