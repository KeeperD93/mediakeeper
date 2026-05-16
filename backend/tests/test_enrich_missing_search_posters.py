"""Background enrichment of search documents stamped with empty poster_url.

The Emby-index sync calls ``upsert_search_document`` without TMDB visual
assets to avoid an I/O cascade. ``enrich_missing_search_posters`` runs
later from the scheduler to hydrate those rows lazily — these tests pin
the early-return, the happy path, the TMDB-has-no-poster skip and the
batch-limit honoring.
"""
from __future__ import annotations

import pytest

from services.portal import search_index
from services.portal.search_index import enrich_missing_search_posters


async def _seed_doc(db_session, *, tmdb_id: int, popularity: float = 0.0) -> None:
    """Create one search document with an empty poster_url."""
    await search_index.upsert_search_document(
        db_session,
        tmdb_id=tmdb_id,
        media_type="movie",
        title=f"Title {tmdb_id}",
        year=2024,
        popularity=popularity,
        poster_url="",
        backdrop_url="",
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_enrich_skips_when_no_empty_docs(db_session):
    """No PortalSearchDocument has an empty poster_url → early return."""
    await search_index.upsert_search_document(
        db_session,
        tmdb_id=1,
        media_type="movie",
        title="Already enriched",
        year=2024,
        poster_url="https://image.tmdb.org/t/p/w300/already.jpg",
    )
    await db_session.commit()

    result = await enrich_missing_search_posters(
        db_session, limit=10, sleep_between_calls=0,
    )
    assert result == {"scanned": 0, "enriched": 0, "skipped": 0}


@pytest.mark.asyncio
async def test_enrich_populates_poster_when_tmdb_returns_one(
    db_session, monkeypatch,
):
    """Happy path: TMDB returns a poster + backdrop → both fields hydrated."""
    await _seed_doc(db_session, tmdb_id=42)

    async def fake_get_media_detail(media_type, tmdb_id, db):
        return {
            "id": tmdb_id,
            "poster": "https://image.tmdb.org/t/p/w300/abc.jpg",
            "backdrop": "https://image.tmdb.org/t/p/w780/bg.jpg",
        }

    monkeypatch.setattr("services.tmdb.get_media_detail", fake_get_media_detail)

    result = await enrich_missing_search_posters(
        db_session, limit=10, sleep_between_calls=0,
    )
    assert result["scanned"] == 1
    assert result["enriched"] == 1
    assert result["skipped"] == 0

    from sqlalchemy import select
    from models.portal.search_document import PortalSearchDocument
    doc = (await db_session.execute(
        select(PortalSearchDocument).where(PortalSearchDocument.tmdb_id == 42)
    )).scalar_one()
    assert doc.poster_url == "https://image.tmdb.org/t/p/w300/abc.jpg"
    assert doc.backdrop_url == "https://image.tmdb.org/t/p/w780/bg.jpg"


@pytest.mark.asyncio
async def test_enrich_skips_doc_when_tmdb_has_no_poster(db_session, monkeypatch):
    """TMDB itself has no visual → leave the row empty, count as skipped."""
    await _seed_doc(db_session, tmdb_id=77)

    async def fake_get_media_detail(media_type, tmdb_id, db):
        return {"id": tmdb_id, "poster": "", "backdrop": ""}

    monkeypatch.setattr("services.tmdb.get_media_detail", fake_get_media_detail)

    result = await enrich_missing_search_posters(
        db_session, limit=10, sleep_between_calls=0,
    )
    assert result["scanned"] == 1
    assert result["enriched"] == 0
    assert result["skipped"] == 1

    from sqlalchemy import select
    from models.portal.search_document import PortalSearchDocument
    doc = (await db_session.execute(
        select(PortalSearchDocument).where(PortalSearchDocument.tmdb_id == 77)
    )).scalar_one()
    assert doc.poster_url == ""


@pytest.mark.asyncio
async def test_enrich_respects_limit(db_session, monkeypatch):
    """Five docs available, limit=3 → only three processed this run."""
    for tmdb_id in range(1, 6):
        await _seed_doc(db_session, tmdb_id=tmdb_id, popularity=tmdb_id)

    async def fake_get_media_detail(media_type, tmdb_id, db):
        return {
            "id": tmdb_id,
            "poster": f"https://image.tmdb.org/t/p/w300/{tmdb_id}.jpg",
            "backdrop": "",
        }

    monkeypatch.setattr("services.tmdb.get_media_detail", fake_get_media_detail)

    result = await enrich_missing_search_posters(
        db_session, limit=3, sleep_between_calls=0,
    )
    assert result["scanned"] == 3
