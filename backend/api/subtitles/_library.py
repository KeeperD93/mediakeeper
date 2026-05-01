"""OpenSubtitles status + Emby library browsing with subtitle status."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.opensubtitles import browse_library, get_emby_libraries, is_configured

router = APIRouter()


@router.get("/status")
async def status(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return {"configured": await is_configured(db)}


@router.get("/libraries")
async def libraries(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List the Emby libraries."""
    return await get_emby_libraries(db)


@router.get("/library")
async def library(
    start: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    type: str = Query("Movie,Episode"),
    library_id: str = Query("", alias="library"),
    search: str = Query(""),
    languages: str = Query(""),
    status: str = Query(""),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Browse the Emby library with subtitle status."""
    lang_list = [lang.strip() for lang in languages.split(",") if lang.strip()] if languages else None
    return await browse_library(
        db, start_index=start, limit=limit, item_types=type,
        search=search, parent_id=library_id, languages=lang_list,
        status_filter=status,
    )
