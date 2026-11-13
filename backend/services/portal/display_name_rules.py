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
    table runs before and after NFKD and casefold: decomposed letters (Cyrillic yi),
    casefolded ones (capital palochka) and mathematical capitals only reach it after."""
    folded = unicodedata.normalize("NFKD", (name or "").translate(_LOOKALIKES)).casefold()
    folded = folded.translate(_LOOKALIKES)
    kept = "".join(ch for ch in folded if "a" <= ch <= "z" or "0" <= ch <= "9")
    # Latin shapes a reader mixes up: I, l and 1 (once casefolded: i, l, 1), O and 0,
    # « rn » and « m ».
    return kept.replace("rn", "m").translate(_SAME_SHAPE)


_RESERVED_SKELETONS = frozenset(display_name_skeleton(n) for n in RESERVED_DISPLAY_NAMES)


def is_reserved_display_name(name: str) -> bool:
    return display_name_skeleton(name) in _RESERVED_SKELETONS


# Blank fillers and joiners with no ink of their own: a name could hide behind them.
_BLANKS = frozenset({0x034F, 0x115F, 0x1160, 0x2800, 0x3164, 0xFFA0})
# Zero-width non-joiner and joiner: part of Persian words and emoji, so allowed
# between two visible characters, never at an edge or next to a space.
_JOINERS = frozenset({0x200C, 0x200D})
_EDGES = re.compile(r"^[\s﻿]+|[\s﻿]+$")


def clean_display_name(raw: str | None) -> str:
    """A submitted name as it is judged and stored: tags stripped, clipped, and
    trimmed of spaces and byte-order marks, as the browser trims it."""
    return _EDGES.sub("", strip_tags_and_trim(raw, max_len=dn.MAX_LENGTH))


def _visible(ch: str) -> bool:
    return unicodedata.category(ch) not in ("Mn", "Me", "Cf") and ord(ch) not in _BLANKS


def _hides_text(name: str) -> bool:
    """Characters that can make a name blank or show it as another one: controls,
    private-use and unassigned code points, line breaks, blank fillers, and format
    characters (direction marks, zero-width spaces) save a joiner between two
    visible characters."""
    for i, ch in enumerate(name):
        category = unicodedata.category(ch)
        if category in ("Cc", "Co", "Cn", "Zl", "Zp") or ord(ch) in _BLANKS:
            return True
        if category == "Cf":
            joined = (
                ord(ch) in _JOINERS
                and 0 < i < len(name) - 1
                and _visible(name[i - 1]) and not name[i - 1].isspace()
                and _visible(name[i + 1]) and not name[i + 1].isspace()
            )
            if not joined:
                return True
    return False


def _has_ink(name: str) -> bool:
    """At least one letter, digit or symbol to see."""
    return any(unicodedata.category(ch)[0] in "LNS" for ch in name if _visible(ch))


def _visible_length(name: str) -> int:
    """Characters a reader counts: combining marks and invisible ones aside."""
    return sum(1 for ch in name if _visible(ch))


def _fold(name: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKC", name).casefold()
        if unicodedata.category(ch) != "Cf" and ord(ch) not in _BLANKS
        and not 0xFE00 <= ord(ch) <= 0xFE0F
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
    if _visible_length(name) < dn.MIN_LENGTH:
        return dn.TOO_SHORT
    if not admin_override and not must_set and is_display_name_locked(profile):
        return dn.LOCKED
    if await is_display_name_taken(db, name, exclude_user_id=profile.user_id):
        return dn.TAKEN
    return dn.FREE
