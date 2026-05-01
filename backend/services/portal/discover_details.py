"""Full media details (with credits, videos, recommendations) + TMDB multi-search."""
import re
import os
import logging
import unicodedata
from difflib import SequenceMatcher
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, tuple_

from core.http_client import get_external_client
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.tmdb import _get_tmdb_key, _tmdb_headers_sync, TMDB_BASE
from services.portal.discover_lists import _normalize, _IMG_BASE
from services.portal.discover_filters import LANGUAGE_TO_REGION
from services.portal.discover_details_enrich import (
    pick_certification,
    pick_watch_providers,
    extract_key_crew,
    extract_videos,
    extract_reviews,
    extract_studios,
    merge_original_language_videos,
)

logger = logging.getLogger("mediakeeper.portal.discover")
LANGUAGE = os.getenv("TMDB_LANGUAGE", "fr-FR")
_SEARCH_TOKEN_RE = re.compile(r"^([\"'([{]*)([^\W_]+)([\"')\]},.;:!?]*)$", re.UNICODE)
_REPEATED_LETTER_RE = re.compile(r"([^\W_])\1{2,}", re.IGNORECASE)
_REDUCIBLE_REPEATED_LETTER_RE = re.compile(r"([^\W_])\1+", re.IGNORECASE)
_REPEATED_NORMALIZED_LETTER_RE = re.compile(r"([^\W_])\1{2,}", re.IGNORECASE)
_SEARCH_SEPARATOR_RE = re.compile(r"[\s\-_.:/\\|,;!?()[\]{}\"'`´’‘“”]+", re.UNICODE)
_SEARCH_STOP_WORDS = {
    "a", "an", "and", "at", "au", "aux", "d", "das", "de", "del",
    "dem", "den", "der", "des", "di", "die", "du", "e", "ein", "eine",
    "el", "en", "et", "for", "from", "gli", "il", "in", "la", "las",
    "le", "les", "lo", "los", "of", "on", "ou", "the", "to", "un",
    "una", "und", "une", "with", "y",
    "aos", "as", "com", "con", "da", "das", "do", "dos", "na", "nas",
    "no", "nos", "o", "os", "para", "per", "por", "sur", "um", "uma",
    "uns", "umas",
}
_SEARCH_TRANSLATION = str.maketrans({
    "ß": "ss", "ẞ": "SS",
    "æ": "ae", "Æ": "AE",
    "œ": "oe", "Œ": "OE",
    "ø": "o", "Ø": "O",
    "ð": "d", "Ð": "D",
    "þ": "th", "Þ": "TH",
    "ł": "l", "Ł": "L",
    "ı": "i", "İ": "I",
})
_SEARCH_MAX_VARIANTS = 18
_SEARCH_MAX_UPSTREAM_REQUESTS = 24
_COMPOUND_SPLIT_OVERRIDES = {
    "xmen": "x men",
    "spiderman": "spider man",
    "spiderverse": "spider verse",
    "antman": "ant man",
}
_COMPOUND_SPLIT_WORDS = {
    "and", "de", "des", "du", "el", "la", "le", "les", "of", "the", "us",
    "america", "anneaux", "ant", "apes", "araignee", "bad", "ball",
    "bat", "better", "black", "blade", "bleu", "breaking", "call", "captain",
    "casa", "cite", "civil", "criminal", "criminel", "criminelle", "dark", "dead",
    "death", "doctor", "dragon", "enquete", "fast", "furious", "galaxy",
    "game", "ghost", "grand", "guardians", "harry", "home", "homme", "impossible",
    "investigation", "iron", "jurassic", "knight", "last", "lord", "man",
    "men", "mission", "note", "panther", "papel", "park", "piece",
    "peur", "planet", "potter", "rings", "runner", "saul", "seigneur", "soldier",
    "space", "spider", "star", "strange", "stranger", "things", "thrones",
    "trek", "walking", "war", "wars", "winter", "woman", "world",
}
_COMPOUND_CONNECTOR_WORDS = {
    word for word in _SEARCH_STOP_WORDS if len(word) <= 4
}


async def get_full_details(
    db: AsyncSession, media_type: str, tmdb_id: int, language: str | None = None,
) -> dict | None:
    """
    Full media details: cast, crew, budget, runtime, etc.
    ``language`` is an ISO 639-1 code (e.g. "fr"); expanded to "fr-FR" if needed.
    """
    api_key = await _get_tmdb_key(db)
    if language:
        lang = language if "-" in language else f"{language.lower()}-{language.upper()}"
    else:
        lang = LANGUAGE
    try:
        client = get_external_client()
        ratings_field = "release_dates" if media_type == "movie" else "content_ratings"
        primary_lang = lang.split("-")[0]
        video_langs = ",".join(dict.fromkeys([primary_lang, "en", "null"]))
        res = await client.get(
            f"{TMDB_BASE}/{media_type}/{tmdb_id}",
            params={
                "language": lang,
                "include_video_language": video_langs,
                "append_to_response": (
                    "credits,videos,recommendations,"
                    "keywords,reviews,external_ids,watch/providers,"
                    f"{ratings_field}"
                ),
            },
            headers=_tmdb_headers_sync(api_key),
        )
        if res.status_code != 200:
            return None
        d = res.json()

        if not (d.get("overview") or "").strip() and primary_lang != "en":
            try:
                res_en = await client.get(
                    f"{TMDB_BASE}/{media_type}/{tmdb_id}",
                    params={"language": "en-US"},
                    headers=_tmdb_headers_sync(api_key),
                )
                if res_en.status_code == 200:
                    en_overview = (res_en.json().get("overview") or "").strip()
                    if en_overview:
                        d["overview"] = en_overview
            except Exception as exc:
                logger.debug(f"[DISCOVER] overview en-US fallback failed: {exc}")

        title = d.get("title") or d.get("name", "")
        date_key = "release_date" if media_type == "movie" else "first_air_date"
        year = d.get(date_key, "")[:4] if d.get(date_key) else ""

        crew = d.get("credits", {}).get("crew", [])
        directors = [
            {"id": c.get("id"), "name": c["name"],
             "photo": f"{_IMG_BASE}/w185{c['profile_path']}" if c.get("profile_path") else None}
            for c in crew if c.get("job") == "Director"
        ]
        key_crew = extract_key_crew(crew)

        cast_raw = d.get("credits", {}).get("cast", [])[:20]
        cast = [{
            "id": c.get("id"),
            "name": c["name"],
            "character": c.get("character", ""),
            "photo": f"{_IMG_BASE}/w185{c['profile_path']}" if c.get("profile_path") else None,
        } for c in cast_raw]

        original_lang = d.get("original_language") or ""
        await merge_original_language_videos(
            client, media_type, tmdb_id, api_key, d, primary_lang, original_lang,
        )
        video_priority = [primary_lang, "en"]
        if original_lang and original_lang not in video_priority:
            video_priority.append(original_lang)
        videos = extract_videos(d.get("videos", {}), language_priority=video_priority)
        recs = [_normalize(r) for r in d.get("recommendations", {}).get("results", [])[:20]]

        kw_payload = d.get("keywords", {}) or {}
        raw_kw = kw_payload.get("keywords") or kw_payload.get("results") or []
        keywords = [k.get("name", "") for k in raw_kw if k.get("name")]

        reviews = extract_reviews(d.get("reviews", {}))
        studios = extract_studios(d.get("production_companies", []))
        countries = [c.get("name", "") for c in d.get("production_countries", [])]
        languages = [
            lang.get("english_name") or lang.get("name") or ""
            for lang in d.get("spoken_languages", [])
        ]

        external = d.get("external_ids", {}) or {}

        result = {
            "id": d.get("id"),
            "tmdb_id": d.get("id"),
            "title": title,
            "original_title": d.get("original_title") or d.get("original_name", ""),
            "year": year,
            "overview": d.get("overview", ""),
            "poster": f"{_IMG_BASE}/w500{d['poster_path']}" if d.get("poster_path") else "",
            "backdrop": f"{_IMG_BASE}/w1280{d['backdrop_path']}" if d.get("backdrop_path") else "",
            "vote": round(d.get("vote_average", 0), 1),
            "vote_count": d.get("vote_count", 0),
            "popularity": round(d.get("popularity", 0), 1),
            "genres": [g.get("name", "") for g in d.get("genres", [])],
            "media_type": media_type,
            "directors": directors,
            "key_crew": key_crew,
            "cast": cast,
            "videos": videos,
            "recommendations": recs,
            "tagline": d.get("tagline", ""),
            "keywords": keywords,
            "reviews": reviews,
            "watch_providers": pick_watch_providers(d),
            "studios": studios,
            "countries": countries,
            "languages": languages,
            "original_language": d.get("original_language", ""),
            "homepage": d.get("homepage", ""),
            "imdb_id": external.get("imdb_id", ""),
            "certification": pick_certification(d, media_type),
        }

        collection = d.get("belongs_to_collection")
        if collection:
            result["collection"] = {
                "id": collection.get("id"),
                "name": collection.get("name", ""),
                "poster": f"{_IMG_BASE}/w300{collection['poster_path']}" if collection.get("poster_path") else None,
                "backdrop": f"{_IMG_BASE}/w780{collection['backdrop_path']}" if collection.get("backdrop_path") else None,
            }

        if media_type == "movie":
            result["runtime"] = d.get("runtime", 0)
            result["budget"] = d.get("budget", 0)
            result["revenue"] = d.get("revenue", 0)
            result["release_date"] = d.get("release_date", "")
            result["status"] = d.get("status", "")
        else:
            result["seasons_count"] = d.get("number_of_seasons", 0)
            result["episodes_count"] = d.get("number_of_episodes", 0)
            result["status"] = d.get("status", "")
            result["networks"] = [n.get("name", "") for n in d.get("networks", [])]
            result["created_by"] = [c.get("name", "") for c in d.get("created_by", [])]

        return result
    except Exception as e:
        logger.error(f"[DISCOVER] Error get_full_details({media_type}/{tmdb_id}): {e}")
        return None


async def get_person_filmography(
    db: AsyncSession, person_id: int,
    role: str = "all", media_filter: str = "all",
) -> dict:
    """Return a person's full filmography (as director or as cast).

    ``role`` = "director" | "acting" | "all"
    ``media_filter`` = "movie" | "tv" | "all"
    """
    api_key = await _get_tmdb_key(db)
    try:
        client = get_external_client()
        res_info = await client.get(
            f"{TMDB_BASE}/person/{person_id}",
            params={"language": LANGUAGE},
            headers=_tmdb_headers_sync(api_key),
        )
        res_credits = await client.get(
            f"{TMDB_BASE}/person/{person_id}/combined_credits",
            params={"language": LANGUAGE},
            headers=_tmdb_headers_sync(api_key),
        )
        info = res_info.json() if res_info.status_code == 200 else {}
        creds = res_credits.json() if res_credits.status_code == 200 else {}

        items = []
        if role in ("all", "acting"):
            items += creds.get("cast", [])
        if role in ("all", "director"):
            items += [c for c in creds.get("crew", []) if c.get("job") == "Director"]

        if media_filter in ("movie", "tv"):
            items = [i for i in items if i.get("media_type") == media_filter]

        seen: dict = {}
        for it in items:
            key = (it.get("id"), it.get("media_type"))
            if key not in seen or (it.get("popularity") or 0) > (seen[key].get("popularity") or 0):
                seen[key] = it
        items = sorted(seen.values(), key=lambda x: x.get("popularity", 0), reverse=True)
        normalized = [_normalize(i) for i in items]

        return {
            "person": {
                "id": info.get("id"),
                "name": info.get("name", ""),
                "photo": f"{_IMG_BASE}/w300{info['profile_path']}" if info.get("profile_path") else None,
                "biography": info.get("biography", ""),
                "known_for": info.get("known_for_department", ""),
            },
            "items": normalized,
        }
    except Exception as e:
        logger.error(f"[DISCOVER] person filmography error: {e}")
        return {"person": None, "items": []}


async def get_collection(db: AsyncSession, collection_id: int) -> dict:
    """Return the parts of a TMDB collection (franchise)."""
    api_key = await _get_tmdb_key(db)
    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/collection/{collection_id}",
            params={"language": LANGUAGE},
            headers=_tmdb_headers_sync(api_key),
        )
        if res.status_code != 200:
            return {"collection": None, "items": []}
        d = res.json()
        items = sorted(d.get("parts", []), key=lambda x: x.get("release_date") or "")
        return {
            "collection": {
                "id": d.get("id"),
                "name": d.get("name", ""),
                "overview": d.get("overview", ""),
                "poster": f"{_IMG_BASE}/w500{d['poster_path']}" if d.get("poster_path") else None,
                "backdrop": f"{_IMG_BASE}/w1280{d['backdrop_path']}" if d.get("backdrop_path") else None,
            },
            "items": [_normalize(i) for i in items],
        }
    except Exception as e:
        logger.error(f"[DISCOVER] collection error: {e}")
        return {"collection": None, "items": []}


async def search_tmdb_multi(
    db: AsyncSession, query: str, page: int = 1, *, available_only: bool = False,
    language: str | None = None,
) -> list[dict]:
    """Search movies + TV shows together."""
    api_key = await _get_tmdb_key(db)
    languages = _search_languages(language)
    try:
        client = get_external_client()
        ranked: dict[tuple[int, str], dict] = {}
        requests_count = 0
        for variant_idx, variant in enumerate(_search_query_variants(query)):
            for language_idx, lang in enumerate(languages):
                if requests_count >= _SEARCH_MAX_UPSTREAM_REQUESTS:
                    break
                requests_count += 1
                results = await _fetch_search_page(client, api_key, variant, page, lang)
                for position, raw in enumerate(results):
                    if raw.get("media_type") not in ("movie", "tv"):
                        continue
                    item = _normalize(raw)
                    if not item.get("tmdb_id"):
                        continue
                    key = (int(item["tmdb_id"]), item["media_type"])
                    score = _score_search_result(
                        query, raw, variant_idx, position, language_idx,
                    )
                    current = ranked.get(key)
                    if not current or score > current["score"]:
                        ranked[key] = {"item": item, "score": score}
            if requests_count >= _SEARCH_MAX_UPSTREAM_REQUESTS:
                break

        items = [
            entry["item"]
            for entry in sorted(
                ranked.values(),
                key=lambda entry: (
                    entry["score"],
                    entry["item"].get("popularity") or 0,
                    entry["item"].get("vote") or 0,
                ),
                reverse=True,
            )
        ]
        if available_only:
            items = await _filter_available(db, items)
        return items[:20]
    except Exception as e:
        logger.error(f"[DISCOVER] Search error: {e}")
        return []


async def _fetch_search_page(
    client, api_key: str, query: str, page: int, language: str,
) -> list[dict]:
    res = await client.get(
        f"{TMDB_BASE}/search/multi",
        params={"query": query, "language": language, "page": page},
        headers=_tmdb_headers_sync(api_key),
    )
    return res.json().get("results", [])[:20]


async def _filter_available(db: AsyncSession, items: list[dict]) -> list[dict]:
    if not items:
        return []
    pairs = {(int(i["tmdb_id"]), i["media_type"]) for i in items if i.get("tmdb_id")}
    if not pairs:
        return []
    rows = (await db.execute(
        select(EmbyTmdbIndex.tmdb_id, EmbyTmdbIndex.media_type)
        .where(tuple_(EmbyTmdbIndex.tmdb_id, EmbyTmdbIndex.media_type).in_(list(pairs)))
    )).all()
    available = {(r[0], r[1]) for r in rows}
    return [i for i in items if (int(i["tmdb_id"]), i["media_type"]) in available]


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
    expanded = query.replace("&", " and ")
    expanded = re.sub(r"\s*\+\s*", " ", expanded)
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


def _is_search_word(normalized_word: str) -> bool:
    return (
        len(normalized_word) >= 4
        and normalized_word.isalpha()
        and normalized_word not in _SEARCH_STOP_WORDS
    )


def _is_latin_search_word(normalized_word: str) -> bool:
    return _is_search_word(normalized_word) and any("a" <= c <= "z" for c in normalized_word)


def _canonical_search_text(value: str) -> str:
    text = _strip_diacritics(value or "").lower()
    text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
    words = [
        _singularize_normalized_word(_soft_correct_normalized_word(word))
        for word in text.split()
        if word not in _SEARCH_STOP_WORDS
    ]
    return " ".join(words)


def _query_years(value: str) -> set[str]:
    return set(re.findall(r"\b(?:19|20)\d{2}\b", value or ""))


def _media_year(raw: dict) -> str:
    date_value = raw.get("release_date") or raw.get("first_air_date") or ""
    match = re.match(r"(\d{4})", date_value)
    return match.group(1) if match else ""


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


def _compact_search_text(value: str) -> str:
    return "".join(value.split())


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


def _strip_diacritics(value: str) -> str:
    value = (value or "").translate(_SEARCH_TRANSLATION)
    return "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )
