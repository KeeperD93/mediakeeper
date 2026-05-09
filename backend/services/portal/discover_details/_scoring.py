"""Search result relevance scoring (title overlap, fuzzy match, year boost)."""
from difflib import SequenceMatcher

from ._text_helpers import (
    _canonical_search_text,
    _compact_search_text,
    _media_year,
    _query_years,
)


def _score_search_result(
    query: str,
    raw: dict,
    variant_idx: int,
    position: int,
    language_idx: int = 0,
) -> float:
    query_text = _canonical_search_text(query)
    if not query_text:
        return 0

    query_years = _query_years(query)
    q_ordered_tokens = [token for token in query_text.split() if token not in query_years]
    if not q_ordered_tokens:
        q_ordered_tokens = query_text.split()
    q_tokens = set(q_ordered_tokens)
    query_for_title = " ".join(q_ordered_tokens)
    titles = [
        raw.get("title") or raw.get("name") or "",
        raw.get("original_title") or raw.get("original_name") or "",
    ]
    best = 0.0
    for title in titles:
        title_text = _canonical_search_text(title)
        if not title_text:
            continue
        t_tokens = set(title_text.split())
        overlap = len(q_tokens & t_tokens) / max(len(q_tokens), 1)
        fuzzy_overlap = _fuzzy_token_overlap(q_tokens, t_tokens)
        order_score = _ordered_token_match(q_ordered_tokens, title_text.split())
        ratio = SequenceMatcher(None, query_for_title, title_text).ratio()
        compact_ratio = SequenceMatcher(
            None,
            _compact_search_text(query_for_title),
            _compact_search_text(title_text),
        ).ratio()
        score = (
            ratio * 32
            + compact_ratio * 28
            + overlap * 18
            + fuzzy_overlap * 32
            + order_score * 22
        )
        if title_text == query_for_title:
            score += 90
        elif _compact_search_text(title_text) == _compact_search_text(query_for_title):
            score += 65
        elif title_text.startswith(query_for_title) or query_for_title.startswith(title_text):
            score += 25
        elif query_for_title in title_text:
            score += 15
        if q_tokens and q_tokens.issubset(t_tokens):
            score += 35
        elif q_tokens and fuzzy_overlap >= 0.92:
            score += 20
        best = max(best, score)

    if query_years:
        title_tokens = {
            token
            for title in titles
            for token in _canonical_search_text(title).split()
        }
        if query_years & title_tokens:
            best += 25
        else:
            media_year = _media_year(raw)
            if media_year in query_years:
                best += 45
            elif media_year:
                best -= 12

    popularity = raw.get("popularity") or 0
    try:
        popularity_bonus = min(float(popularity), 100.0) * 0.03
    except (TypeError, ValueError):
        popularity_bonus = 0
    position_bonus = max(0, 20 - position) * 0.05
    variant_penalty = variant_idx * 0.4
    language_penalty = language_idx * 0.25
    return best + popularity_bonus + position_bonus - variant_penalty - language_penalty


def _fuzzy_token_overlap(q_tokens: set[str], t_tokens: set[str]) -> float:
    if not q_tokens:
        return 0.0
    if not t_tokens:
        return 0.0
    total = 0.0
    for q_token in q_tokens:
        best = max(SequenceMatcher(None, q_token, t_token).ratio() for t_token in t_tokens)
        threshold = 0.72 if len(q_token) >= 7 else 0.82
        if best >= threshold:
            total += best
    return total / len(q_tokens)


def _ordered_token_match(q_tokens: list[str], t_tokens: list[str]) -> float:
    if not q_tokens:
        return 0.0
    if not t_tokens:
        return 0.0

    matched = 0
    t_index = 0
    for q_token in q_tokens:
        best_index = -1
        best_ratio = 0.0
        for idx in range(t_index, len(t_tokens)):
            ratio = SequenceMatcher(None, q_token, t_tokens[idx]).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = idx
            if ratio >= 0.94:
                break
        threshold = 0.72 if len(q_token) >= 7 else 0.82
        if best_index >= 0 and best_ratio >= threshold:
            matched += 1
            t_index = best_index + 1
    return matched / len(q_tokens)
