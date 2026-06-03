"""Behavioural contract for the Emby to TMDB index sync helpers."""
import pytest
from sqlalchemy import select

from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.portal.emby_index import _sync, _upsert_index, sync_emby_tmdb_index


@pytest.mark.asyncio
async def test_upsert_index_skips_write_when_nothing_changed(db_session):
    """An unchanged item must not bump ``updated_at`` — proof that the sync no
    longer rewrites every row on each pass, so it can run every few minutes
    cheaply. A real field change must still bump it via the column onupdate."""
    await _upsert_index(db_session, "emby-1", 100, "movie", "Title")
    await db_session.commit()
    row = (await db_session.execute(
        select(EmbyTmdbIndex).where(EmbyTmdbIndex.emby_item_id == "emby-1")
    )).scalar_one()
    first_updated = row.updated_at

    # Same data again -> flush no-op, updated_at untouched.
    await _upsert_index(db_session, "emby-1", 100, "movie", "Title")
    await db_session.commit()
    await db_session.refresh(row)
    assert row.updated_at == first_updated

    # A real change -> UPDATE emitted -> onupdate bumps updated_at.
    await _upsert_index(db_session, "emby-1", 100, "movie", "Renamed")
    await db_session.commit()
    await db_session.refresh(row)
    assert row.title == "Renamed"
    assert row.updated_at != first_updated


class _FakeResp:
    status_code = 200

    def __init__(self, items):
        self._items = items

    def json(self):
        return {"Items": self._items, "TotalRecordCount": len(self._items)}


@pytest.mark.asyncio
async def test_recent_mode_indexes_new_items_without_purging(db_session, monkeypatch):
    """Recent mode upserts the newest items but must NOT purge index rows
    whose Emby item is outside the small window (it has no full view)."""
    # Pre-existing row whose item is not in the recent window.
    await _upsert_index(db_session, "old-emby", 999, "movie", "Old Movie")
    await db_session.commit()

    async def fake_source(_db):
        return {"source": "emby", "url": "http://emby.test", "api_key": "k"}

    async def fake_tmdb_key(_db):
        return None  # items carry ProviderIds, so the TMDB cascade is unused

    class FakeClient:
        async def get(self, url, params=None, headers=None):
            # Recent mode must request the DateCreated sort and the small limit.
            assert params["SortBy"] == "DateCreated"
            assert params["Limit"] == "50"
            if params["IncludeItemTypes"] == "Movie":
                return _FakeResp([{
                    "Id": "new-emby", "Name": "New Movie",
                    "ProductionYear": 2024, "ProviderIds": {"Tmdb": "555"},
                }])
            return _FakeResp([])

    monkeypatch.setattr(_sync, "get_active_media_source", fake_source)
    monkeypatch.setattr(_sync, "_get_tmdb_key", fake_tmdb_key)
    monkeypatch.setattr(_sync, "get_internal_client", lambda: FakeClient())

    result = await sync_emby_tmdb_index(db_session, recent_limit=50)

    assert result["synced"] == 1
    assert result["purged"] == 0
    new_row = (await db_session.execute(
        select(EmbyTmdbIndex).where(EmbyTmdbIndex.emby_item_id == "new-emby")
    )).scalar_one()
    assert new_row.tmdb_id == 555
    # The out-of-window row survived (no purge in recent mode).
    survived = (await db_session.execute(
        select(EmbyTmdbIndex).where(EmbyTmdbIndex.emby_item_id == "old-emby")
    )).scalar_one_or_none()
    assert survived is not None
