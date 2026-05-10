"""Bridge between Emby audio tags (ISO 639-2) and TMDB original_language (ISO 639-1).

Emby's ``PlaybackSession.audio_language`` carries 3-letter codes such as
``"fre"`` or ``"jpn"`` — sometimes suffixed with a region (``"fre-FR"``).
TMDB returns 2-letter codes (``"fr"``, ``"ja"``).

The mapping below covers the languages we expect to actually meet in a
self-hosted media library. Anything outside the mapping returns ``None``
from :func:`to_iso639_2`, and :func:`audio_matches_original` simply
returns ``False`` — better to undercount the Purist trophy than to
falsely unlock it on an ambiguous code.
"""
from __future__ import annotations


# 2-letter (TMDB) → 3-letter (Emby) for the languages we care about.
# Source order: top library hits + any locale we ship the UI in.
ISO_639_1_TO_2: dict[str, str] = {
    "fr": "fre",
    "en": "eng",
    "ja": "jpn",
    "ko": "kor",
    "es": "spa",
    "de": "ger",
    "it": "ita",
    "ru": "rus",
    "pt": "por",
    "zh": "chi",
    "ar": "ara",
    "hi": "hin",
    "nl": "dut",
    "sv": "swe",
    "tr": "tur",
    "pl": "pol",
}

# Reverse lookup, including the alternative ISO 639-2/T forms Emby may
# emit for languages where 639-2/B and 639-2/T diverge (e.g. ``"fra"`` vs
# ``"fre"``, ``"deu"`` vs ``"ger"``). Built once at import-time.
_ISO_639_2_TO_1: dict[str, str] = {v: k for k, v in ISO_639_1_TO_2.items()}
_ISO_639_2_TO_1.update({
    "fra": "fr",
    "deu": "de",
    "zho": "zh",
    "nld": "nl",
})


def to_iso639_2(code_1: str | None) -> str | None:
    """Map a 2-letter language code to its 3-letter equivalent.

    Returns ``None`` for falsy input or unknown codes — never raises.
    Comparison is case-insensitive.
    """
    if not code_1:
        return None
    return ISO_639_1_TO_2.get(code_1.strip().lower())


def audio_matches_original(
    audio_lang: str | None,
    original_lang: str | None,
) -> bool:
    """True iff the Emby audio code matches the TMDB original-language code.

    Tolerant of the region suffix Emby occasionally appends (e.g. ``"fre-FR"``).
    Both arguments must be non-empty; either ``None`` is treated as a miss.
    """
    if not audio_lang or not original_lang:
        return False
    expected = to_iso639_2(original_lang)
    if not expected:
        return False
    audio_prefix = audio_lang.strip().lower().split("-", 1)[0]
    return audio_prefix == expected


def to_display_code(audio_lang: str | None) -> str | None:
    """Map an Emby audio language code to a 2-letter uppercase display code.

    Tolerant of region suffixes (``"fre-FR"`` → ``"FR"``) and of either
    639-2/B (``"fre"``) or 639-2/T (``"fra"``) variants. Returns ``None``
    for unknown or empty input — never raises. Used by the watchlist
    scanner to surface available audio languages on episodes.
    """
    if not audio_lang:
        return None
    code = audio_lang.strip().lower().split("-", 1)[0]
    if not code:
        return None
    if len(code) == 2 and code in ISO_639_1_TO_2:
        return code.upper()
    mapped = _ISO_639_2_TO_1.get(code)
    return mapped.upper() if mapped else None
