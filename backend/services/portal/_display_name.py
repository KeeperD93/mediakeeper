"""Anonymous display-name resolution for user-facing portal surfaces.

Privacy boundary: user-facing endpoints must NEVER expose the raw Emby
username when an account has not picked its own portal pseudo. Silent
accounts render as a stable, friendly ``Renard-Bleu-42`` / ``Blue-Fox-42``
pseudo derived from ``user_id`` (see :mod:`_pseudo_words`), localized to
the viewer — so the same account renders identically across the chat, the
leaderboard, the activity feed and any other user-to-user surface without
revealing the underlying identifier. Admin endpoints keep the raw Emby
``username`` in a dedicated field for operators who need it.

The backoffice administrator never gets a random pseudo: it always renders
as the localized ``Administrateur`` / ``Administrator`` label.
"""
from __future__ import annotations

from services.portal._pseudo_words import generate_pseudo

_ADMIN_LABEL_FR = "Administrateur"
_ADMIN_LABEL_EN = "Administrator"


def _is_en(lang: str | None) -> bool:
    return (lang or "").lower().startswith("en")


def resolve_display_name(
    username: str | None,
    user_id: int,
    lang: str = "fr",
    *,
    is_admin: bool = False,
) -> str:
    """Resolve the public name for a user.

    Order: the admin label wins, then an explicitly-set pseudo, then the
    generated anonymous pseudo for accounts that never picked one.
    """
    if is_admin:
        return _ADMIN_LABEL_EN if _is_en(lang) else _ADMIN_LABEL_FR
    if username is not None and username.strip():
        return username.strip()
    return generate_pseudo(user_id, lang)


def parse_accept_language(header: str | None) -> str:
    if not header:
        return "fr"
    # Cheap scan — we only care whether English appears anywhere in the
    # preference list (q-weights and regions are ignored on purpose).
    for token in header.split(","):
        primary = token.split(";", 1)[0].strip().lower()
        if primary.startswith("en"):
            return "en"
    return "fr"
