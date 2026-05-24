"""Maintenance: remove library from cache, resolve series image, migrate library_name."""
from fastapi import APIRouter, Depends
from sqlalchemy import delete as sa_delete
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.playback_stats import LibraryCache, PlaybackSession
from models.user import User

router = APIRouter()


@router.delete("/libraries/{lib_id}")
async def delete_library_cache(
    lib_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Remove a library from the local cache."""
    result = await db.execute(sa_delete(LibraryCache).where(LibraryCache.lib_id == lib_id))
    await db.commit()
    return {"deleted": result.rowcount > 0, "lib_id": lib_id}


@router.get("/series/image/{series_name:path}")
async def series_image_id(
    series_name: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Resolve a series name to its Emby ID for the image."""
    from services.emby import search_series_id
    sid = await search_series_id(db, series_name)
    return {"series_id": sid}


@router.post("/migrate/library-names")
async def migrate_library_names(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """One-shot migration: resolve NULL library_name values via the Emby Ancestors API."""
    from services.settings import get_active_media_source
    from services.stats import _item_lib_cache, _resolve_library_name

    source = await get_active_media_source(db)
    if not source:
        return {"error": "no_active_media_source"}

    url = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    if not url or not api_key:
        return {"error": "missing_url_or_api_key"}

    rows_res = await db.execute(
        select(PlaybackSession).where(
            or_(
                PlaybackSession.library_name.is_(None),
                PlaybackSession.library_name == "Séries",
                PlaybackSession.library_name == "Films",
            )
        )
    )
    rows = rows_res.scalars().all()

    migrated = 0
    fallback = 0
    errors = 0
    for row in rows:
        try:
            lib = await _resolve_library_name(row.item_id, url, api_key, db)
            if lib:
                row.library_name = lib
                migrated += 1
            else:
                if row.item_type == "Episode" or row.series_name:
                    row.library_name = "Séries"
                    fallback += 1
                elif row.item_type == "Movie":
                    row.library_name = "Films"
                    fallback += 1
        except Exception:
            errors += 1

    await db.commit()
    return {
        "total_null": len(rows),
        "migrated": migrated,
        "fallback": fallback,
        "errors": errors,
        "cache_size": len(_item_lib_cache),
    }
