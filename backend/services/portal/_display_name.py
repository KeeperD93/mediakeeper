"""Anonymous display-name resolution for user-facing portal surfaces.

Privacy boundary (Rules §22): user-facing endpoints must NEVER expose the
raw Emby username when an account has not picked its own portal pseudo.
Admin endpoints stay raw on purpose (operators need to see who hasn't
set a name yet).

The alias is deterministic (salted hash of ``user_id``) so the same
silent account always renders as the same "Utilisateur 1234" across the
chat, the leaderboard, the activity feed and any other user-to-user
surface — without revealing the underlying identifier.
"""
from __future__ import annotations

import hashlib

STABLE_USER_TAG_SALT = "mediakeeper-portal-pseudo-v1"
STABLE_USER_TAG_MOD = 10_000


def stable_user_tag(user_id: int) -> str:
    digest = hashlib.sha256(
        f"{STABLE_USER_TAG_SALT}:{user_id}".encode("utf-8")
    ).hexdigest()
    return str(int(digest, 16) % STABLE_USER_TAG_MOD).zfill(4)


def resolve_display_name(
    username: str | None, user_id: int, lang: str = "fr"
) -> str:
    if username is not None and username.strip():
        return username.strip()
    tag = stable_user_tag(user_id)
    if (lang or "").lower().startswith("en"):
        return f"User {tag}"
    return f"Utilisateur {tag}"


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
