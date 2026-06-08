"""Maintenance: remove library from cache, resolve series image, migrate library_name."""
from fastapi import APIRouter, Depends
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.playback_stats import LibraryCache
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
    """Re-resolve library names that are missing or not a real Emby library
    (a sub-folder / slug such as ``Archives``) via the Emby Ancestors API.

    Thin wrapper over the shared repair routine — the same repair also runs
    automatically with the periodic library-cache refresh."""
    from services.stats_aggregator.libraries import repair_library_names

    return await repair_library_names(db)
