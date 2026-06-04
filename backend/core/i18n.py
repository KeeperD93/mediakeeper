"""Request locale resolution — the single source for the viewer's language.

The frontend sends its active UI locale in the ``X-MK-Locale`` header on
every request (see frontend ``apiClient.buildApiHeaders``). That header is
the authoritative "what the user is actually looking at" locale — it follows
the global admin preference AND the portal's ephemeral per-session language.
The browser ``Accept-Language`` and the configured default are fallbacks.

This locale drives both app-generated text and external (TMDB) content so a
viewer in English gets English everywhere. Adding a language is additive: the
frontend locale file + (optionally) one TMDB region entry — no change here.
"""
import os

from fastapi import Header

# No-header fallback only (server jobs, curl) — the frontend always sends one.
DEFAULT_LOCALE = os.getenv("MK_DEFAULT_LOCALE", "fr")


def normalize_locale(raw: str | None) -> str | None:
    """Return the language base of a locale tag (``"pt-BR"`` -> ``"pt"``), or
    None when absent / malformed."""
    if not raw:
        return None
    base = raw.strip().lower().replace("_", "-").split("-", 1)[0]
    return base if base.isalpha() and 2 <= len(base) <= 3 else None


def resolve_locale(x_mk_locale: str | None, accept_language: str | None) -> str:
    """Viewer locale: explicit app header > first Accept-Language tag > default."""
    return (
        normalize_locale(x_mk_locale)
        or normalize_locale((accept_language or "").split(",", 1)[0])
        or DEFAULT_LOCALE
    )


async def get_request_locale(
    x_mk_locale: str | None = Header(default=None, alias="x-mk-locale"),
    accept_language: str | None = Header(default=None, alias="accept-language"),
) -> str:
    """FastAPI dependency returning the viewer's chosen content locale."""
    return resolve_locale(x_mk_locale, accept_language)
