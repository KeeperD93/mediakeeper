"""Long-term Portal catalog search index.

The public search path uses this module first. TMDB search remains an
enrichment fallback, while PostgreSQL keeps a local fuzzy index backed by
``pg_trgm`` in production.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.search_document import PortalSearchDocument
from services.portal.discover_details import (
    _canonical_search_text,
    _score_search_result,
    _search_query_variants,
    search_tmdb_multi,
)

logger = logging.getLogger("mediakeeper.portal.search")

_LOCAL_PAGE_SIZE = 20
_LOCAL_CANDIDATE_LIMIT = 160
_LOCAL_STRONG_SCORE = 130.0
_LOCAL_MIN_SCORE = 55.0


async def search_catalog(
    db: AsyncSession,
    query: str,
    page: int = 1,
    *,
    available_only: bool = False,
    language: str | None = None,
) -> list[dict]:
    """Search the local index first, then fall back to TMDB when needed."""
    local_entries = await search_local_index_entries(
        db, query, page=page, available_only=available_only,
    )
    if _local_entries_are_enough(local_entries):
        return [entry["item"] for entry in local_entries]

    fallback_items = await search_tmdb_multi(
        db, query, page, available_only=available_only, language=language,
    )
    if fallback_items:
        await _cache_fallback_items(db, fallback_items, available_on_emby=available_only)

    return _merge_local_and_fallback(local_entries, fallback_items)


async def search_local_index(
    db: AsyncSession,
    query: str,
    page: int = 1,
    *,
    available_only: bool = False,
) -> list[dict]:
    entries = await search_local_index_entries(
        db, query, page=page, available_only=available_only,
    )
    return [entry["item"] for entry in entries]


async def search_local_index_entries(
    db: AsyncSession,
    query: str,
    page: int = 1,
    *,
    available_only: bool = False,
) -> list[dict]:
    variants = _search_query_variants(query)
    if not variants:
        return []

    docs = await _load_candidate_documents(db, variants, available_only=available_only)
    ranked: dict[tuple[int, str], dict] = {}
    for position, doc in enumerate(docs):
        raw = _document_to_raw(doc)
        score = max(
            _score_search_result(variant, raw, variant_idx, position)
            for variant_idx, variant in enumerate(variants[:8])
        )
        if score < _LOCAL_MIN_SCORE:
            continue
        key = (doc.tmdb_id, doc.media_type)
        item = _document_to_item(doc)
        current = ranked.get(key)
        if not current or score > current["score"]:
            ranked[key] = {"item": item, "score": score}

    ordered = sorted(
        ranked.values(),
        key=lambda entry: (
            entry["score"],
            entry["item"].get("popularity") or 0,
            entry["item"].get("vote") or 0,
        ),
        reverse=True,
    )
    start = max(page - 1, 0) * _LOCAL_PAGE_SIZE
    return ordered[start:start + _LOCAL_PAGE_SIZE]


async def upsert_search_document(
    db: AsyncSession,
    *,
    tmdb_id: int,
    media_type: str,
    title: str,
    original_title: str | None = None,
    year: int | str | None = None,
    overview: str | None = None,
    poster_url: str | None = None,
    backdrop_url: str | None = None,
    vote_average: float | int | None = 0,
    popularity: float | int | None = 0,
    genres: list[int] | str | None = None,
    available_on_emby: bool = False,
    source: str = "tmdb",
) -> PortalSearchDocument | None:
    clean_title = (title or "").strip()
    if not tmdb_id or media_type not in {"movie", "tv"} or not clean_title:
        return None

    result = await db.execute(
        select(PortalSearchDocument).where(
            PortalSearchDocument.tmdb_id == int(tmdb_id),
            PortalSearchDocument.media_type == media_type,
        )
    )
    doc = result.scalar_one_or_none()
    year_int = _coerce_year(year)
    genres_text = _serialize_genres(genres)
    search_text = _build_document_search_text(clean_title, original_title, year_int)
    now = datetime.now(timezone.utc)

    values = {
        "title": clean_title,
        "original_title": (original_title or "").strip() or None,
        "search_text": search_text,
        "year": year_int,
        "overview": overview or "",
        "vote_average": _coerce_float(vote_average),
        "popularity": _coerce_float(popularity),
        "genres": genres_text,
        "source": source,
        "updated_at": now,
    }
    # Only refresh visual assets when the caller actually supplied
    # them. The Emby-index sync (``_index_ops._upsert_index``) calls
    # this function without ``poster_url`` / ``backdrop_url`` to mark a
    # title as available — without this guard it overwrote the TMDB
    # URLs previously cached, leaving search results with a blank
    # placeholder where the poster used to be.
    if poster_url is not None:
        values["poster_url"] = poster_url
    if backdrop_url is not None:
        values["backdrop_url"] = backdrop_url
    if doc is None:
        doc = PortalSearchDocument(
            tmdb_id=int(tmdb_id),
            media_type=media_type,
            available_on_emby=available_on_emby,
            poster_url=poster_url or "",
            backdrop_url=backdrop_url or "",
            **{k: v for k, v in values.items() if k not in ("poster_url", "backdrop_url")},
        )
    else:
        for key, value in values.items():
            setattr(doc, key, value)
        doc.available_on_emby = bool(doc.available_on_emby or available_on_emby)
    db.add(doc)
    return doc


async def upsert_search_document_from_item(
    db: AsyncSession,
    item: dict,
    *,
    available_on_emby: bool = False,
    source: str = "tmdb",
) -> PortalSearchDocument | None:
    return await upsert_search_document(
        db,
        tmdb_id=item.get("tmdb_id") or item.get("id"),
        media_type=item.get("media_type") or "movie",
        title=item.get("title") or "",
        year=item.get("year"),
        overview=item.get("overview"),
        poster_url=item.get("poster_url") or item.get("poster"),
        backdrop_url=item.get("backdrop"),
        vote_average=item.get("vote"),
        popularity=item.get("popularity"),
        genres=item.get("genres"),
        available_on_emby=available_on_emby,
        source=source,
    )


async def refresh_search_availability(db: AsyncSession) -> None:
    """Mirror the current Emby/TMDB index into the search index."""
    docs = (await db.execute(select(PortalSearchDocument))).scalars().all()
    if not docs:
        return
    rows = (await db.execute(
        select(EmbyTmdbIndex.tmdb_id, EmbyTmdbIndex.media_type)
    )).all()
    available = {(int(row[0]), row[1]) for row in rows}
    for doc in docs:
        doc.available_on_emby = (doc.tmdb_id, doc.media_type) in available
    await db.flush()


async def _load_candidate_documents(
    db: AsyncSession,
    variants: list[str],
    *,
    available_only: bool,
) -> list[PortalSearchDocument]:
    dialect = _session_dialect(db)
    if dialect == "postgresql":
        return await _load_postgres_candidates(db, variants, available_only=available_only)
    return await _load_generic_candidates(db, available_only=available_only)


async def _load_postgres_candidates(
    db: AsyncSession,
    variants: list[str],
    *,
    available_only: bool,
) -> list[PortalSearchDocument]:
    await db.execute(text("SELECT set_config('pg_trgm.similarity_threshold', '0.12', true)"))
    seen: set[int] = set()
    docs: list[PortalSearchDocument] = []
    for variant in variants[:8]:
        canonical = _canonical_search_text(variant)
        if not canonical:
            continue
        lower_search_text = func.lower(PortalSearchDocument.search_text)
        lower_title = func.lower(PortalSearchDocument.title)
        lower_original = func.lower(func.coalesce(PortalSearchDocument.original_title, ""))
        db_score = func.greatest(
            func.similarity(lower_search_text, canonical),
            func.similarity(lower_title, canonical),
            func.similarity(lower_original, canonical),
        )
        conditions = [db_score >= 0.08]
        conditions.extend(
            lower_search_text.like(f"%{token}%")
            for token in canonical.split()
            if len(token) >= 3
        )
        stmt = (
            select(PortalSearchDocument, db_score.label("db_score"))
            .where(or_(*conditions))
            .order_by(db_score.desc(), PortalSearchDocument.popularity.desc())
            .limit(_LOCAL_CANDIDATE_LIMIT)
        )
        if available_only:
            stmt = stmt.where(PortalSearchDocument.available_on_emby.is_(True))

        for doc, _score in (await db.execute(stmt)).all():
            if doc.id in seen:
                continue
            seen.add(doc.id)
            docs.append(doc)
            if len(docs) >= _LOCAL_CANDIDATE_LIMIT:
                return docs
    return docs


async def _load_generic_candidates(
    db: AsyncSession,
    *,
    available_only: bool,
) -> list[PortalSearchDocument]:
    stmt = select(PortalSearchDocument)
    if available_only:
        stmt = stmt.where(PortalSearchDocument.available_on_emby.is_(True))
    stmt = stmt.order_by(PortalSearchDocument.popularity.desc()).limit(_LOCAL_CANDIDATE_LIMIT)
    return list((await db.execute(stmt)).scalars().all())


async def _cache_fallback_items(
    db: AsyncSession,
    items: list[dict],
    *,
    available_on_emby: bool,
) -> None:
    try:
        for item in items:
            await upsert_search_document_from_item(
                db,
                item,
                available_on_emby=available_on_emby,
                source="tmdb_search",
            )
        await db.commit()
    except Exception:
        await db.rollback()
        logger.debug("[PORTAL_SEARCH] fallback cache update failed", exc_info=True)


def _local_entries_are_enough(entries: list[dict]) -> bool:
    if not entries:
        return False
    return entries[0]["score"] >= _LOCAL_STRONG_SCORE or len(entries) >= _LOCAL_PAGE_SIZE


def _merge_local_and_fallback(local_entries: list[dict], fallback_items: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[tuple[int, str]] = set()
    for entry in local_entries:
        item = entry["item"]
        key = (int(item["tmdb_id"]), item["media_type"])
        seen.add(key)
        merged.append(item)
    for item in fallback_items:
        key = (int(item["tmdb_id"]), item["media_type"])
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged[:_LOCAL_PAGE_SIZE]


def _build_document_search_text(
    title: str,
    original_title: str | None,
    year: int | None,
) -> str:
    parts = [title]
    if original_title and original_title != title:
        parts.append(original_title)
    if year:
        parts.append(str(year))

    expanded: list[str] = []
    for part in parts:
        expanded.append(part)
        expanded.extend(_search_query_variants(part))

    seen: set[str] = set()
    out: list[str] = []
    for part in expanded:
        canonical = _canonical_search_text(part)
        if canonical and canonical not in seen:
            seen.add(canonical)
            out.append(canonical)
    return " ".join(out)


def _document_to_raw(doc: PortalSearchDocument) -> dict:
    date_key = "release_date" if doc.media_type == "movie" else "first_air_date"
    title_key = "title" if doc.media_type == "movie" else "name"
    original_key = "original_title" if doc.media_type == "movie" else "original_name"
    return {
        "id": doc.tmdb_id,
        "media_type": doc.media_type,
        title_key: doc.title,
        original_key: doc.original_title or doc.title,
        date_key: f"{doc.year}-01-01" if doc.year else "",
        "vote_average": doc.vote_average or 0,
        "popularity": doc.popularity or 0,
    }


def _document_to_item(doc: PortalSearchDocument) -> dict:
    year = str(doc.year) if doc.year else ""
    return {
        "id": doc.tmdb_id,
        "tmdb_id": doc.tmdb_id,
        "title": doc.title,
        "year": year,
        "overview": doc.overview or "",
        "poster": doc.poster_url or "",
        "poster_url": doc.poster_url or "",
        "backdrop": doc.backdrop_url or "",
        "vote": round(doc.vote_average or 0, 1),
        "popularity": doc.popularity or 0,
        "genres": _parse_genres(doc.genres),
        "media_type": doc.media_type,
        "available_on_emby": bool(doc.available_on_emby),
    }


def _session_dialect(db: AsyncSession) -> str:
    bind = db.get_bind()
    return bind.dialect.name if bind is not None else ""


def _coerce_year(value: int | str | None) -> int | None:
    if value is None:
        return None
    raw = str(value)[:4]
    return int(raw) if raw.isdigit() else None


def _coerce_float(value: float | int | str | None) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _serialize_genres(value: list[int] | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return ",".join(str(item) for item in value)


def _parse_genres(value: str | None) -> list[int]:
    genres: list[int] = []
    for part in (value or "").split(","):
        part = part.strip()
        if part.isdigit():
            genres.append(int(part))
    return genres
