"""Upsert + playback de la table emby_tmdb_index."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.portal.search_index import upsert_search_document


async def _upsert_index(
    db: AsyncSession,
    emby_item_id: str,
    tmdb_id: int,
    media_type: str,
    title: str,
):
    """Insert or update an index entry."""
    result = await db.execute(
        select(EmbyTmdbIndex).where(EmbyTmdbIndex.emby_item_id == emby_item_id)
    )
    entry = result.scalar_one_or_none()
    if entry:
        entry.tmdb_id = tmdb_id
        entry.media_type = media_type
        entry.title = title
        entry.updated_at = datetime.now(timezone.utc)
    else:
        entry = EmbyTmdbIndex(
            emby_item_id=emby_item_id,
            tmdb_id=tmdb_id,
            media_type=media_type,
            title=title,
        )
    db.add(entry)
    await upsert_search_document(
        db,
        tmdb_id=tmdb_id,
        media_type=media_type,
        title=title,
        available_on_emby=True,
        source="emby",
    )


async def is_available_on_emby(
    db: AsyncSession, tmdb_id: int, media_type: str
) -> bool:
    """Check if a TMDB item is available in the Emby library.

    ``.limit(1)`` guards against the rare case where the same TMDB id
    has multiple index rows (re-import in flight) — without it,
    ``scalar_one_or_none`` would raise MultipleResultsFound.
    """
    result = await db.execute(
        select(EmbyTmdbIndex.id).where(
            EmbyTmdbIndex.tmdb_id == tmdb_id,
            EmbyTmdbIndex.media_type == media_type,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_emby_item_by_tmdb(
    db: AsyncSession, tmdb_id: int, media_type: str
) -> dict | None:
    """Get the Emby item ID for a TMDB ID. Same dup-tolerance as above."""
    result = await db.execute(
        select(EmbyTmdbIndex).where(
            EmbyTmdbIndex.tmdb_id == tmdb_id,
            EmbyTmdbIndex.media_type == media_type,
        ).limit(1)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        return None
    return {
        "emby_item_id": entry.emby_item_id,
        "tmdb_id": entry.tmdb_id,
        "media_type": entry.media_type,
        "title": entry.title,
    }
