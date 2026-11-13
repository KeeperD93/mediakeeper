"""Rules a display name must pass when a member picks one.

The live check, the profile update and the first-login wizard all ask
``judge_display_name``: a name the check accepts is a name the save accepts.
"""
import unicodedata
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants import display_name as dn
from models.portal.profile import UserProfile
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


def display_name_skeleton(name: str) -> str:
    """What a name reads as: look-alike letters, accents, width, case, invisible
    characters and punctuation folded away, only ``a-z`` and ``0-9`` kept."""
    folded = unicodedata.normalize("NFKD", (name or "").translate(_LOOKALIKES)).casefold()
    return "".join(ch for ch in folded if "a" <= ch <= "z" or "0" <= ch <= "9")


_RESERVED_SKELETONS = frozenset(display_name_skeleton(n) for n in RESERVED_DISPLAY_NAMES)


def is_reserved_display_name(name: str) -> bool:
    return display_name_skeleton(name) in _RESERVED_SKELETONS


def _has_format_characters(name: str) -> bool:
    """Invisible and direction-changing characters (Unicode category Cf), which can
    make a name show as another one."""
    return any(unicodedata.category(ch) == "Cf" for ch in name)


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
    """Verdict on ``name`` (already stripped of tags and trimmed) for ``profile``:
    ``current`` or ``free`` when it may be kept or taken, else the refusal.

    A member who still owes a name (first login, or reset by an admin) cannot
    confirm the stored one: it is the random placeholder or the name the admin
    reset. The reserved check runs before « same as now », so a reserved name
    stored by an older path cannot be kept either.
    """
    if not name or _has_format_characters(name):
        return dn.INVALID
    is_admin = profile.role == ROLE_ADMIN
    # An admin never owes a public name: the flag is masked for them everywhere.
    must_set = bool(profile.display_name_must_set) and not is_admin
    lowered = name.lower()
    stored = (profile.display_name or "").lower()
    if must_set:
        if lowered == stored:
            return dn.PREVIOUS if profile.display_name_changed_at else dn.GENERATED
        if lowered in {generate_pseudo(profile.user_id, lang).lower() for lang in ("fr", "en")}:
            return dn.GENERATED
    if not is_admin and is_reserved_display_name(name):
        return dn.RESERVED
    if lowered == stored:
        return dn.CURRENT
    if len(name) < dn.MIN_LENGTH:
        return dn.TOO_SHORT
    if not admin_override and not must_set and is_display_name_locked(profile):
        return dn.LOCKED
    if await is_display_name_taken(db, name, exclude_user_id=profile.user_id):
        return dn.TAKEN
    return dn.FREE
