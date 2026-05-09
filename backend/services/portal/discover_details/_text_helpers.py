"""Pure text utilities (diacritics, canonical form, language codes, year extraction)."""
import re
import unicodedata

from services.portal.discover_filters import LANGUAGE_TO_REGION

from ._constants import (
    LANGUAGE,
    _REPEATED_NORMALIZED_LETTER_RE,
    _SEARCH_STOP_WORDS,
    _SEARCH_TRANSLATION,
)


def _strip_diacritics(value: str) -> str:
    value = (value or "").translate(_SEARCH_TRANSLATION)
    return "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )


def _is_search_word(normalized_word: str) -> bool:
    return (
        len(normalized_word) >= 4
        and normalized_word.isalpha()
        and normalized_word not in _SEARCH_STOP_WORDS
    )


def _is_latin_search_word(normalized_word: str) -> bool:
    return _is_search_word(normalized_word) and any("a" <= c <= "z" for c in normalized_word)


def _soft_correct_normalized_word(word: str) -> str:
    corrected = _REPEATED_NORMALIZED_LETTER_RE.sub(r"\1\1", word)
    if corrected.endswith("quet"):
        return f"{corrected}e"
    if corrected.endswith(("ell", "enn", "ett", "iqu")):
        return f"{corrected}e"
    return corrected


def _singularize_normalized_word(word: str) -> str:
    if len(word) >= 5 and word.endswith("ies"):
        return f"{word[:-3]}y"
    if (
        len(word) >= 4
        and word.endswith("s")
        and not word.endswith(("ss", "ous", "ius", "sis", "us"))
    ):
        return word[:-1]
    return word


def _canonical_search_text(value: str) -> str:
    text = _strip_diacritics(value or "").lower()
    text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
    words = [
        _singularize_normalized_word(_soft_correct_normalized_word(word))
        for word in text.split()
        if word not in _SEARCH_STOP_WORDS
    ]
    return " ".join(words)


def _compact_search_text(value: str) -> str:
    return "".join(value.split())


def _query_years(value: str) -> set[str]:
    return set(re.findall(r"\b(?:19|20)\d{2}\b", value or ""))


def _media_year(raw: dict) -> str:
    date_value = raw.get("release_date") or raw.get("first_air_date") or ""
    match = re.match(r"(\d{4})", date_value)
    return match.group(1) if match else ""


def _tmdb_language(language: str | None) -> str:
    raw = (language or "").strip().replace("_", "-")
    if not raw:
        return LANGUAGE
    if "-" in raw:
        return raw
    code = raw.lower()
    region = LANGUAGE_TO_REGION.get(code[:2], code[:2].upper())
    return f"{code}-{region}"


def _search_languages(language: str | None) -> list[str]:
    candidates = [_tmdb_language(language), LANGUAGE, "en-US"]
    seen: set[str] = set()
    out: list[str] = []
    for candidate in candidates:
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            out.append(candidate)
    return out
