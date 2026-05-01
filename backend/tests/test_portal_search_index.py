"""Portal local search index."""

import pytest

from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.portal import search_index


@pytest.mark.asyncio
async def test_local_index_matches_missing_separators(db_session):
    await search_index.upsert_search_document(
        db_session,
        tmdb_id=100,
        media_type="movie",
        title="Mission: Impossible",
        year=1996,
        popularity=10,
    )
    await db_session.commit()

    items = await search_index.search_local_index(db_session, "missionimpossible")

    assert [item["tmdb_id"] for item in items] == [100]


@pytest.mark.asyncio
async def test_catalog_search_prefers_strong_local_index(monkeypatch, db_session):
    await search_index.upsert_search_document(
        db_session,
        tmdb_id=200,
        media_type="tv",
        title="Enquêtes criminelles",
        year=2024,
        popularity=3,
    )
    await db_session.commit()

    async def forbidden_tmdb_search(*_args, **_kwargs):
        raise AssertionError("TMDB should not be called for a strong local match")

    monkeypatch.setattr(search_index, "search_tmdb_multi", forbidden_tmdb_search)

    items = await search_index.search_catalog(db_session, "enquet criminellle")

    assert [item["tmdb_id"] for item in items] == [200]


@pytest.mark.asyncio
async def test_catalog_search_caches_tmdb_fallback(monkeypatch, db_session):
    async def fake_tmdb_search(*_args, **_kwargs):
        return [{
            "id": 300,
            "tmdb_id": 300,
            "title": "Spider-Man",
            "year": "2002",
            "overview": "",
            "poster": "",
            "poster_url": "",
            "backdrop": "",
            "vote": 7.3,
            "popularity": 50,
            "genres": [28],
            "media_type": "movie",
        }]

    monkeypatch.setattr(search_index, "search_tmdb_multi", fake_tmdb_search)

    items = await search_index.search_catalog(db_session, "spiderman")
    cached = await search_index.search_local_index(db_session, "spider man")

    assert [item["tmdb_id"] for item in items] == [300]
    assert [item["tmdb_id"] for item in cached] == [300]


@pytest.mark.asyncio
async def test_refresh_search_availability_follows_emby_index(db_session):
    await search_index.upsert_search_document(
        db_session,
        tmdb_id=400,
        media_type="movie",
        title="Le Grand Bleu",
        available_on_emby=True,
    )
    await db_session.commit()

    await search_index.refresh_search_availability(db_session)
    items = await search_index.search_local_index(
        db_session, "legrandbleu", available_only=True,
    )
    assert items == []

    db_session.add(EmbyTmdbIndex(
        emby_item_id="emby-400",
        tmdb_id=400,
        media_type="movie",
        title="Le Grand Bleu",
    ))
    await db_session.commit()

    await search_index.refresh_search_availability(db_session)
    items = await search_index.search_local_index(
        db_session, "legrandbleu", available_only=True,
    )
    assert [item["tmdb_id"] for item in items] == [400]
