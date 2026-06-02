"""Behavioural contract for the Emby to TMDB index sync helpers."""
import pytest
from sqlalchemy import select

from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.portal.emby_index import _upsert_index


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
