"""Normalisation des codes langue ISO 639-1 ↔ 639-2/B."""

_LANG_ALIASES = {
    "fr": "fre", "fre": "fre", "fra": "fre", "french": "fre",
    "en": "eng", "eng": "eng", "english": "eng",
    "es": "spa", "spa": "spa", "spanish": "spa",
    "de": "ger", "ger": "ger", "deu": "ger", "german": "ger",
    "it": "ita", "ita": "ita", "italian": "ita",
    "pt": "por", "por": "por", "portuguese": "por",
    "nl": "dut", "dut": "dut", "nld": "dut", "dutch": "dut",
    "ru": "rus", "rus": "rus", "russian": "rus",
    "ja": "jpn", "jpn": "jpn", "japanese": "jpn",
    "zh": "chi", "chi": "chi", "zho": "chi", "chinese": "chi",
    "ko": "kor", "kor": "kor", "korean": "kor",
    "ar": "ara", "ara": "ara", "arabic": "ara",
    "pl": "pol", "pol": "pol", "polish": "pol",
    "sv": "swe", "swe": "swe", "swedish": "swe",
    "da": "dan", "dan": "dan", "danish": "dan",
    "no": "nor", "nor": "nor", "norwegian": "nor",
    "fi": "fin", "fin": "fin", "finnish": "fin",
    "tr": "tur", "tur": "tur", "turkish": "tur",
    "cs": "cze", "cze": "cze", "ces": "cze", "czech": "cze",
    "ro": "rum", "rum": "rum", "ron": "rum", "romanian": "rum",
    "hu": "hun", "hun": "hun", "hungarian": "hun",
    "el": "gre", "gre": "gre", "ell": "gre", "greek": "gre",
    "he": "heb", "heb": "heb", "hebrew": "heb",
    "th": "tha", "tha": "tha", "thai": "tha",
    "vi": "vie", "vie": "vie", "vietnamese": "vie",
    "id": "ind", "ind": "ind", "indonesian": "ind",
    "uk": "ukr", "ukr": "ukr", "ukrainian": "ukr",
    "hi": "hin", "hin": "hin", "hindi": "hin",
}


def _normalize_lang(code: str) -> str:
    """Normalise un code langue vers ISO 639-2/B (3 lettres)."""
    return _LANG_ALIASES.get(code.lower().strip(), code.lower().strip())
