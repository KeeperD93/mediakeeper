"""The "Recommended for you" home row must fill to 20 distinct items.

It is the only home row that filters candidates against the Emby library
index, so page-1 popular titles in the user's genres (usually already in
the library) get removed and the row used to fall short of 20. It now
pulls extra TMDB pages, deduped, until it reaches 20.
"""
from unittest.mock import AsyncMock, patch

import pytest

from models.user import User
from models.portal.profile import UserProfile
from services.portal import personal_recos

_DB = object()  # never touched: every DB-backed call is patched below


def _page(endpoint, page):
    """Twenty synthetic TMDB results; ids are disjoint per type and page."""
    base = 0 if "movie" in endpoint else 100
    start = base + (page - 1) * 20 + 1
    media_type = "movie" if base == 0 else "tv"
    return [{"tmdb_id": start + k, "media_type": media_type} for k in range(20)]


def _profile():
    return UserProfile(
        favorite_genres=[28], hide_adult=False, language="fr", display_name="u",
    )


def _patches(*, fetch, indexed):
    return (
        patch.object(personal_recos, "_infer_genres_from_history", AsyncMock(return_value=[])),
        patch.object(personal_recos, "_fetch_list_params", fetch),
        patch.object(personal_recos, "_get_indexed_tmdb_ids", indexed),
    )


@pytest.mark.asyncio
async def test_row_backfills_to_20_when_page1_mostly_in_library():
    async def fetch(db, endpoint, page, params, **kw):
        return _page(endpoint, page)

    async def indexed(db, media_type):
        return set(range(1, 19)) if media_type == "movie" else set(range(101, 119))

    p1, p2, p3 = _patches(fetch=AsyncMock(side_effect=fetch), indexed=AsyncMock(side_effect=indexed))
    with p1, p2, p3:
        result = await personal_recos.get_recommendations_for_user(_DB, User(username="u"), _profile())

    ids = [r["tmdb_id"] for r in result]
    assert len(result) == 20
    assert len(set(ids)) == 20  # 20 distinct media
    for r in result:
        lib = range(1, 19) if r["media_type"] == "movie" else range(101, 119)
        assert r["tmdb_id"] not in lib  # never a library item


@pytest.mark.asyncio
async def test_row_does_not_backfill_when_page1_already_full():
    async def fetch(db, endpoint, page, params, **kw):
        return _page(endpoint, page)

    fetch_mock = AsyncMock(side_effect=fetch)
    p1, p2, p3 = _patches(fetch=fetch_mock, indexed=AsyncMock(return_value=set()))
    with p1, p2, p3:
        result = await personal_recos.get_recommendations_for_user(_DB, User(username="u"), _profile())

    assert len(result) == 20
    assert fetch_mock.await_count == 2  # only page 1 movie + tv, no extra pages


@pytest.mark.asyncio
async def test_row_dedupes_titles_repeated_across_pages():
    async def fetch(db, endpoint, page, params, **kw):
        if "movie" in endpoint and page == 2:
            # Repeat id 20 (the page-1 survivor) before fresh ids.
            return [{"tmdb_id": 20, "media_type": "movie"}] + [
                {"tmdb_id": i, "media_type": "movie"} for i in range(21, 40)
            ]
        return _page(endpoint, page)

    async def indexed(db, media_type):
        return set(range(1, 20)) if media_type == "movie" else set(range(101, 120))

    p1, p2, p3 = _patches(fetch=AsyncMock(side_effect=fetch), indexed=AsyncMock(side_effect=indexed))
    with p1, p2, p3:
        result = await personal_recos.get_recommendations_for_user(_DB, User(username="u"), _profile())

    ids = [r["tmdb_id"] for r in result]
    assert len(set(ids)) == len(ids)  # no duplicate despite the cross-page repeat
