"""Query variant generation: orthography, plurals, romance suffixes, compound splits."""
from ._constants import (
    _COMPOUND_CONNECTOR_WORDS,
    _COMPOUND_SPLIT_OVERRIDES,
    _COMPOUND_SPLIT_WORDS,
    _REDUCIBLE_REPEATED_LETTER_RE,
    _REPEATED_LETTER_RE,
    _SEARCH_MAX_VARIANTS,
    _SEARCH_SEPARATOR_RE,
    _SEARCH_TOKEN_RE,
)
from ._text_helpers import (
    _canonical_search_text,
    _is_latin_search_word,
    _singularize_normalized_word,
    _soft_correct_normalized_word,
    _strip_diacritics,
)


def _search_query_variants(query: str) -> list[str]:
    base = " ".join((query or "").split()).strip()
    if not base:
        return []

    candidates = [base]
    separated = _normalize_query_separators(base)
    if separated != base:
        candidates.append(separated)

    ampersand = _expand_symbol_words(base)
    if ampersand != base:
        candidates.append(ampersand)

    no_diacritics = _strip_diacritics(base)
    if no_diacritics != base:
        candidates.append(no_diacritics)

    canonical = _canonical_search_text(base)
    if canonical and canonical != base.lower():
        candidates.append(canonical)

    for candidate in list(candidates):
        candidates.append(_map_query_words(candidate, _split_compound_word))

    for candidate in list(candidates):
        candidates.append(_map_query_words(candidate, _soft_correct_word))

    for candidate in list(candidates):
        candidates.append(_map_query_words(candidate, _alternate_romance_suffix_word))

    for candidate in list(candidates):
        candidates.append(_map_query_words(candidate, _pluralize_word))
        candidates.append(_map_query_words(candidate, _singularize_word))

    for candidate in list(candidates):
        candidates.append(_map_query_words(candidate, _reduce_repeated_word))

    seen: set[str] = set()
    variants: list[str] = []
    for candidate in candidates:
        cleaned = " ".join((candidate or "").split()).strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            variants.append(cleaned)
    return variants[:_SEARCH_MAX_VARIANTS]


def _map_query_words(query: str, transform) -> str:
    changed = False
    parts = []
    for token in query.split():
        match = _SEARCH_TOKEN_RE.match(token)
        if not match:
            parts.append(token)
            continue
        prefix, word, suffix = match.groups()
        mapped = transform(word)
        changed = changed or mapped != word
        parts.append(f"{prefix}{mapped}{suffix}")
    return " ".join(parts) if changed else ""


def _normalize_query_separators(query: str) -> str:
    return " ".join(part for part in _SEARCH_SEPARATOR_RE.split(query) if part)


def _expand_symbol_words(query: str) -> str:
    """Expand ``&`` / ``+`` symbols into their word-form so a search like
    ``"Lilo & Stitch"`` or ``"Naruto+Boruto"`` matches the underlying
    title naturally.

    Linear-time rewrite of the previous ``re.sub(r"\\s*\\+\\s*", ...)``
    pattern, which CodeQL flagged as polynomial-degree (py/polynomial-redos
    #144). The ``\\s*X\\s*`` greedy form is O(n²) on inputs of unmatched
    whitespace; ``split``/``join`` is O(n) with the same effective output.
    """
    expanded = query.replace("&", " and ")
    if "+" in expanded:
        expanded = " ".join(part.strip() for part in expanded.split("+"))
    return " ".join(expanded.split())


def _split_compound_word(word: str) -> str:
    normalized = _strip_diacritics(word).lower()
    if normalized in _COMPOUND_SPLIT_OVERRIDES:
        return _COMPOUND_SPLIT_OVERRIDES[normalized]
    if not normalized.isalpha() or len(normalized) < 5 or len(normalized) > 32:
        return word

    parts = _segment_compound_word(normalized)
    if parts:
        return " ".join(parts)
    return word


def _segment_compound_word(value: str) -> list[str] | None:
    memo: dict[tuple[int, int, int, bool], list[str] | None] = {}
    max_parts = 5

    def walk(
        index: int,
        part_count: int,
        strong_count: int,
        last_was_connector: bool,
    ) -> list[str] | None:
        if part_count > max_parts:
            return None
        if index == len(value):
            return (
                []
                if part_count >= 2 and strong_count >= 2 and not last_was_connector
                else None
            )
        key = (index, part_count, min(strong_count, 2), last_was_connector)
        if key in memo:
            return memo[key]

        for end in range(len(value), index + 1, -1):
            piece = value[index:end]
            strength = _compound_piece_strength(piece)
            if strength is None:
                continue
            suffix = walk(
                end,
                part_count + 1,
                strong_count + strength,
                strength == 0,
            )
            if suffix is not None:
                result = [piece, *suffix]
                memo[key] = result
                return result
        memo[key] = None
        return None

    return walk(0, 0, 0, False)


def _compound_piece_strength(piece: str) -> int | None:
    if piece in _COMPOUND_CONNECTOR_WORDS:
        return 0

    candidates = {
        piece,
        _soft_correct_normalized_word(piece),
        _singularize_normalized_word(piece),
        _singularize_normalized_word(_soft_correct_normalized_word(piece)),
    }
    for candidate in list(candidates):
        if candidate.endswith(("nel", "rel", "tel", "iel", "uel")):
            candidates.add(f"{candidate}le")

    if any(candidate in _COMPOUND_SPLIT_WORDS for candidate in candidates):
        return 1
    return None


def _pluralize_word(word: str) -> str:
    normalized = _strip_diacritics(word).lower()
    if not _is_latin_search_word(normalized) or normalized.endswith(("s", "x", "z")):
        return word
    if normalized.endswith("y") and len(normalized) > 1 and normalized[-2] not in "aeiou":
        return f"{word[:-1]}ies"
    if normalized.endswith(("ch", "sh")):
        return f"{word}es"
    if normalized.endswith(("au", "eau", "eu")):
        return f"{word}x"
    return f"{word}s"


def _singularize_word(word: str) -> str:
    normalized = _strip_diacritics(word).lower()
    if not _is_latin_search_word(normalized):
        return word
    if normalized.endswith("ies") and len(normalized) > 4:
        return f"{word[:-3]}y"
    if normalized.endswith(("ches", "shes", "xes", "zes")):
        return word[:-2]
    if (
        not normalized.endswith("s")
        or normalized.endswith(("ss", "ous", "ius", "sis", "us"))
    ):
        return word
    return word[:-1]


def _soft_correct_word(word: str) -> str:
    normalized = _strip_diacritics(word).lower()
    if not _is_latin_search_word(normalized):
        return word

    corrected = _REPEATED_LETTER_RE.sub(r"\1\1", word)
    corrected_normalized = _strip_diacritics(corrected).lower()
    if corrected_normalized.endswith("quet"):
        corrected = f"{corrected}e"
    elif corrected_normalized.endswith(("ell", "enn", "ett")):
        corrected = f"{corrected}e"
    elif corrected_normalized.endswith("iqu"):
        corrected = f"{corrected}e"
    return corrected


def _alternate_romance_suffix_word(word: str) -> str:
    normalized = _strip_diacritics(word).lower()
    if not _is_latin_search_word(normalized):
        return word
    if normalized.endswith(("nel", "rel", "tel", "iel", "uel")):
        return f"{word}le"
    return word


def _reduce_repeated_word(word: str) -> str:
    normalized = _strip_diacritics(word).lower()
    if not _is_latin_search_word(normalized) or not _REDUCIBLE_REPEATED_LETTER_RE.search(word):
        return word
    return _REDUCIBLE_REPEATED_LETTER_RE.sub(r"\1", word)
