"""Activity history: paginated list, minimap, single or bulk deletes."""
import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.stats import get_activity_history, get_activity_minimap

logger = logging.getLogger("mediakeeper.api.stats")
router = APIRouter()


class BulkDeleteRequest(BaseModel):
    ids: list[int]


@router.get("/activity")
async def activity(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=500),
    search: str = Query(""),
    cursor: str = Query(""),
    limit: int = Query(0, ge=0, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Paginated activity history (cursor-based or offset fallback)."""
    return await get_activity_history(db, page=page, per_page=per_page,
                                      search=search, cursor=cursor, limit=limit)


@router.delete("/activity/{activity_id}")
async def delete_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete one activity history row."""
    from models.playback_stats import PlaybackSession
    result = await db.execute(
        select(PlaybackSession).where(PlaybackSession.id == activity_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"error": "Activity not found"}
    await db.delete(row)
    await db.commit()
    logger.info(f"Activity {activity_id} deleted by {_.username}")
    return {"ok": True}


@router.post("/activity/bulk-delete")
async def delete_activities_bulk(
    req: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete several activity history rows."""
    from models.playback_stats import PlaybackSession
    deleted = 0
    for aid in req.ids:
        result = await db.execute(
            select(PlaybackSession).where(PlaybackSession.id == aid)
        )
        row = result.scalar_one_or_none()
        if row:
            await db.delete(row)
            deleted += 1
    await db.commit()
    logger.info(f"{deleted} activity row(s) deleted by {_.username}")
    return {"ok": True, "deleted": deleted}


@router.get("/activity/minimap")
async def activity_minimap(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Playbacks from the last 24h for the minimap (independent of pagination)."""
    return await get_activity_minimap(db)
