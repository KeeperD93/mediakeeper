"""Upsert + playback de la table emby_tmdb_index."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.emby_tmdb_index import EmbyTmdbIndex


async def _upsert_index(
    db: AsyncSession,
    emby_item_id: str,
    tmdb_id: int,
    media_type: str,
    title: str,
    production_year: int | None = None,
    original_language: str | None = None,
    date_created: datetime | None = None,
):
    """Insert or update an index entry.

    ``production_year``, ``original_language`` and ``date_created`` are
    filled lazily: on update we only set them when the DB row still has
    ``NULL`` so a manual refresh (or a TMDB correction) cached on disk
    is never overwritten by a less-informed sync pass.
    """
    result = await db.execute(
        select(EmbyTmdbIndex).where(EmbyTmdbIndex.emby_item_id == emby_item_id)
    )
    entry = result.scalar_one_or_none()
    if entry:
        entry.tmdb_id = tmdb_id
        entry.media_type = media_type
        entry.title = title
        if production_year is not None and entry.production_year is None:
            entry.production_year = production_year
        if original_language is not None and entry.original_language is None:
            entry.original_language = original_language
        if date_created is not None and entry.date_created is None:
            entry.date_created = date_created
        entry.updated_at = datetime.now(timezone.utc)
    else:
        entry = EmbyTmdbIndex(
            emby_item_id=emby_item_id,
            tmdb_id=tmdb_id,
            media_type=media_type,
            title=title,
            production_year=production_year,
            original_language=original_language,
            date_created=date_created,
        )
    db.add(entry)


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
