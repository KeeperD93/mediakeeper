"""Rules a display name must pass when a member picks one.

The live check, the profile update and the first-login wizard all ask
``judge_display_name``: a name the check accepts is a name the save accepts.
"""
import re
import unicodedata
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants import display_name as dn
from models.portal.profile import UserProfile
from services.portal import strip_tags_and_trim
from services.portal._pseudo_words import generate_pseudo, pseudo_word_pairs
from services.portal.admin_users_constants import ROLE_ADMIN
from services.portal.display_name_text import (
    display_name_key,
    display_name_skeleton,
    has_ink,
    hides_text,
    min_length,
    visible_length,
)
from services.portal.profile_serializers import display_name_locked_until

# Only the admin role may wear these, or anything that reads like them.
RESERVED_DISPLAY_NAMES = frozenset({
    "admin", "administrator", "administrateur", "root",
})

_RESERVED_SKELETONS = frozenset(display_name_skeleton(n) for n in RESERVED_DISPLAY_NAMES)
# « admin » opens every admin title (administrator, administratrice…) and closes their
# compounds (sysadmin, SUPERADMIN): a run of pieces that starts or ends with it is
# reserved, not one that only holds it (« Badminton »). « root » only as a whole run,
# so « Groot » and « Rootkit » stay free.
_ADMIN = display_name_skeleton("admin")
_DIGITS = "0123456789"
_PROVISIONAL_PAIRS = frozenset(display_name_skeleton(pair) for pair in pseudo_word_pairs())


def _kind(ch: str) -> str:
    """Letter (marks included), digit, or neither."""
    category = unicodedata.category(ch)[0]
    return "L" if category in "LM" else "N" if category == "N" else ""


def _words(name: str) -> list[str]:
    """Runs of letters, digits and marks."""
    words: list[str] = []
    current = ""
    for ch in name:
        if _kind(ch):
            current += ch
        elif current:
            words.append(current)
            current = ""
    return [*words, current] if current else words


def _pieces(word: str) -> list[str]:
    """A word cut where letters meet digits, where a small letter meets a capital
    (letters without case between them aside), and before the last capital of a
    run of capitals followed by a small letter (« ITAdmin »: « IT », « Admin »)."""
    pieces: list[str] = []
    current, kind, after_small = "", "", False
    for ch in word:
        if current and (_kind(ch) != kind or (ch.isupper() and after_small)):
            pieces.append(current)
            current, after_small = "", False
        elif ch.islower() and len(current) >= 2 and current[-1].isupper() and current[-2].isupper():
            pieces.append(current[:-1])
            current = current[-1]
        current += ch
        kind = _kind(ch)
        if ch.islower() or ch.isupper():
            after_small = ch.islower()
    return [*pieces, current] if current else pieces


def _reads_reserved(text: str) -> bool:
    # Digits only pad a word: dropped before 0 and 1 could read as o and i.
    skeleton = display_name_skeleton(text.strip(_DIGITS))
    return bool(skeleton) and (
        skeleton in _RESERVED_SKELETONS or skeleton.startswith(_ADMIN) or skeleton.endswith(_ADMIN)
    )


def is_reserved_display_name(name: str) -> bool:
    """A reserved name or a look-alike of one, alone or inside the name: any run of
    neighbouring pieces between two spaces, as a sign or an emoji does not part
    words (« Admin MediaKeeper », « ITAdmin », « Root1 », « AdMinistratrice »,
    « SUPERADMIN », « Bob Ad-min »)."""
    if display_name_skeleton(name.strip(_DIGITS)) in _RESERVED_SKELETONS:
        return True
    for chunk in name.split():
        pieces = [piece for word in _words(chunk) for piece in _pieces(word)]
        for start in range(len(pieces)):
            for end in range(start + 1, len(pieces) + 1):
                if _reads_reserved("".join(pieces[start:end])):
                    return True
    return False


def looks_provisional(name: str) -> bool:
    """Shaped like a provisional pseudo: one of its word pairs, in either language,
    then a number from 1 to 99, whatever the separators (« renard bleu 7 »)."""
    folded = display_name_key(name).strip()
    stem = folded.rstrip(_DIGITS)
    number = folded[len(stem):]
    return (
        0 < len(number) <= 2 and int(number) > 0
        and display_name_skeleton(stem) in _PROVISIONAL_PAIRS
    )


_EDGES = re.compile(r"^[\s﻿]+|[\s﻿]+$")


def clean_display_name(raw: str | None) -> str:
    """A submitted name as it is judged and stored: tags stripped, clipped, and
    trimmed of spaces and byte-order marks, as the browser trims it."""
    return _EDGES.sub("", strip_tags_and_trim(raw, max_len=dn.MAX_LENGTH))


def same_name(a: str, b: str) -> bool:
    """The same name to the eye: equal once folded, or equal non-empty skeletons."""
    skeleton = display_name_skeleton(a)
    return display_name_key(a) == display_name_key(b) or (bool(skeleton) and skeleton == display_name_skeleton(b))


def is_display_name_locked(profile: UserProfile) -> bool:
    until = display_name_locked_until(profile)
    return bool(until and until > datetime.now(UTC))


def stored_name_refused(profile: UserProfile) -> bool:
    """A member's stored name no longer passes the rules (it came from older rules
    or from an admin): they may pick another one at once, lock or not, or they
    could neither keep it nor leave it."""
    stored = profile.display_name or ""
    if profile.role == ROLE_ADMIN:
        return False
    return (
        not stored or hides_text(stored) or not has_ink(stored)
        or is_reserved_display_name(stored) or looks_provisional(stored)
    )


async def is_display_name_taken(
    db: AsyncSession, candidate: str, *, exclude_user_id: int | None = None,
) -> bool:
    """Another member shows this name, or one that reads the same: the same key,
    or the same non-empty skeleton. Admins and members who still owe a name hold
    none. An unlocked read: the unique key refuses the second of two saves."""
    key = display_name_key(candidate)
    if not key:
        return False
    skeleton = display_name_skeleton(candidate)
    same = UserProfile.display_name_key == key
    if skeleton:
        same = or_(same, UserProfile.display_name_skeleton == skeleton)
    stmt = select(UserProfile.user_id).where(same).limit(1)
    if exclude_user_id is not None:
        stmt = stmt.where(UserProfile.user_id != exclude_user_id)
    return (await db.execute(stmt)).first() is not None


def _refused_even_if_stored(profile: UserProfile, name: str, *, must_set: bool, is_admin: bool) -> str | None:
    """The refusals that hold before « same as now »: a name still owed cannot be
    the placeholder or the name an admin reset, nor look like them; a reserved
    name or anyone's provisional pseudo cannot be kept from an older path."""
    if must_set:
        if same_name(name, profile.display_name or ""):
            return dn.PREVIOUS if profile.display_name_changed_at else dn.GENERATED
        if any(same_name(name, generate_pseudo(profile.user_id, lang)) for lang in ("fr", "en")):
            return dn.GENERATED
    if not is_admin and is_reserved_display_name(name):
        return dn.RESERVED
    if looks_provisional(name):
        return dn.GENERATED
    return None


async def judge_display_name(
    db: AsyncSession,
    profile: UserProfile,
    name: str,
    *,
    admin_override: bool = False,
) -> str:
    """Verdict on ``name`` (as ``clean_display_name`` returns it) for ``profile``:
    ``current`` or ``free`` when it may be kept or taken, else the refusal.
    The refusals of ``_refused_even_if_stored`` run before « same as now »."""
    if not name or hides_text(name) or not has_ink(name):
        return dn.INVALID
    is_admin = profile.role == ROLE_ADMIN
    # An admin never owes a public name: the flag is masked for them everywhere.
    must_set = bool(profile.display_name_must_set) and not is_admin
    refusal = _refused_even_if_stored(profile, name, must_set=must_set, is_admin=is_admin)
    if refusal:
        return refusal
    if display_name_key(name) == display_name_key(profile.display_name or ""):
        return dn.CURRENT
    if visible_length(name) < min_length(name):
        return dn.TOO_SHORT
    if (
        not admin_override and not must_set
        and is_display_name_locked(profile) and not stored_name_refused(profile)
    ):
        return dn.LOCKED
    if await is_display_name_taken(db, name, exclude_user_id=profile.user_id):
        return dn.TAKEN
    return dn.FREE
