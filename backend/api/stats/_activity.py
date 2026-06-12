"""Activity history: paginated list, minimap, single or bulk deletes."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.stats import (
    get_activity_grouped,
    get_activity_history,
    get_activity_minimap,
    get_activity_users,
)

logger = logging.getLogger("mediakeeper.api.stats")
router = APIRouter()


class BulkDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ids: list[int] = Field(..., min_length=1, max_length=1000)


@router.get("/activity")
async def activity(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=500),
    search: str = Query(""),
    cursor: str = Query(""),
    limit: int = Query(0, ge=0, le=500),
    exclude_users: str = Query(""),
    sort_by: str = Query("started_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Paginated activity history.

    Default (date, newest-first) returns sessions grouped by consecutive
    same-(user, item) runs with cursor paging; any other sort returns a flat,
    server-sorted list with offset paging (grouping only makes sense in
    chronological order).
    """
    if sort_by in ("", "started_at") and sort_order == "desc":
        return await get_activity_grouped(db, limit=limit or per_page, cursor=cursor,
                                          search=search, exclude_users=exclude_users)
    return await get_activity_history(db, page=page, per_page=per_page, search=search,
                                      exclude_users=exclude_users, sort_by=sort_by,
                                      sort_order=sort_order)


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
        raise HTTPException(status_code=404, detail="activity_not_found")
    await db.delete(row)
    await db.commit()
    logger.info("Activity %s deleted by %s", activity_id, _.username)
    return {"ok": True}


@router.post("/activity/bulk-delete")
async def delete_activities_bulk(
    req: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete several activity history rows in a single statement."""
    from models.playback_stats import PlaybackSession
    result = await db.execute(
        delete(PlaybackSession)
        .where(PlaybackSession.id.in_(req.ids))
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    deleted = result.rowcount or 0
    logger.info("%s activity row(s) deleted by %s", deleted, _.username)
    return {"ok": True, "deleted": deleted}


@router.get("/activity/users")
async def activity_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Distinct users present in the activity history (for the display filter)."""
    return await get_activity_users(db)


@router.get("/activity/minimap")
async def activity_minimap(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Playbacks from the last 24h for the minimap (independent of pagination)."""
    return await get_activity_minimap(db)
