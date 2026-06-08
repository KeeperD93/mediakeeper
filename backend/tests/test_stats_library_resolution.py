"""Library-name resolution: collector precedence + repair routine (#269)."""
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.playback_stats import LibraryCache, PlaybackSession
from services.stats_aggregator.libraries import repair_library_names
from services.stats_collector._resolver import _session_library_name

RESOLVER = "services.stats_collector._resolver._resolve_library_name"


@pytest.mark.asyncio
async def test_session_library_prefers_embys_own_library_name():
    """Emby's LibraryName wins outright — the Ancestors API is not even called."""
    resolver = AsyncMock(return_value="Resolved Library")
    with patch(RESOLVER, resolver):
        out = await _session_library_name(
            {"LibraryName": "Movies", "ParentName": "Sub-folder"}, "i1", "http://emby", "k"
        )
    assert out == "Movies"
    resolver.assert_not_awaited()


@pytest.mark.asyncio
async def test_session_library_resolves_collectionfolder_before_parent():
    """No LibraryName → resolve the CollectionFolder, never the parent folder."""
    with patch(RESOLVER, AsyncMock(return_value="Real Library")):
        out = await _session_library_name(
            {"ParentName": "Sub-folder"}, "i1", "http://emby", "k"
        )
    assert out == "Real Library"


@pytest.mark.asyncio
async def test_session_library_uses_parent_only_as_last_resort():
    """ParentName is kept only when Emby gives nothing and resolution fails."""
    with patch(RESOLVER, AsyncMock(return_value=None)):
        out = await _session_library_name(
            {"ParentName": "Sub-folder"}, "i1", "http://emby", "k"
        )
    assert out == "Sub-folder"


@pytest.mark.asyncio
async def test_session_library_none_when_nothing_available():
    with patch(RESOLVER, AsyncMock(return_value=None)):
        out = await _session_library_name({}, "i1", "http://emby", "k")
    assert out is None


def _session(session_key, item_id, library_name):
    return PlaybackSession(
        session_key=session_key,
        user_id="u1",
        user_name="User One",
        item_id=item_id,
        item_name="An Item",
        item_type="Movie",
        library_name=library_name,
    )


@pytest.mark.asyncio
async def test_repair_reresolves_only_non_library_rows(db_session):
    """Rows on a sub-folder/slug or NULL are re-resolved; valid rows untouched."""
    db_session.add(LibraryCache(lib_id="1", name="Movies", collection_type="movies"))
    db_session.add(_session("k1", "i1", "Movies"))      # real library → left alone
    db_session.add(_session("k2", "i2", "Sub-folder"))  # folder → re-resolve
    db_session.add(_session("k3", "i3", None))          # missing → re-resolve
    await db_session.commit()

    with patch(
        "services.stats_aggregator.libraries._repair.get_active_media_source",
        AsyncMock(return_value={"source": "emby", "url": "http://emby", "api_key": "k"}),
    ), patch(
        "services.stats_collector._resolve_library_name",
        AsyncMock(return_value="Movies"),
    ) as resolver:
        result = await repair_library_names(db_session)

    assert result["candidates"] == 2
    assert result["migrated"] == 2
    assert resolver.await_count == 2  # the valid row is never re-resolved

    by_key = {
        r.session_key: r.library_name
        for r in (await db_session.execute(select(PlaybackSession))).scalars().all()
    }
    assert by_key == {"k1": "Movies", "k2": "Movies", "k3": "Movies"}


@pytest.mark.asyncio
async def test_repair_is_noop_without_active_emby_source(db_session):
    """Fresh install / no media source configured → no work, no error raised."""
    with patch(
        "services.stats_aggregator.libraries._repair.get_active_media_source",
        AsyncMock(return_value=None),
    ):
        result = await repair_library_names(db_session)
    assert result == {"error": "no_active_media_source"}
