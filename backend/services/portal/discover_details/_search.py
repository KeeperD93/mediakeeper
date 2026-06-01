"""TMDB multi-search orchestration: variant fan-out, ranking, availability filter."""
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_external_client
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.portal.discover_lists import _normalize
from services.portal.runtime_cache import resolve_runtimes
from services.tmdb import _get_tmdb_key, _tmdb_headers_sync, TMDB_BASE

from ._constants import _SEARCH_MAX_UPSTREAM_REQUESTS, logger
from ._query_variants import _search_query_variants
from ._scoring import _score_search_result
from ._text_helpers import _search_languages


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
        items = items[:20]
        await resolve_runtimes(items)
        return items
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
