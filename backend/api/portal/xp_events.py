"""Admin endpoints for XP boost events (Christmas double-XP, etc.)."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.portal.deps import require_admin
from services.portal import xp_boost as svc

router = APIRouter(prefix="/admin/xp-events", tags=["portal-admin"])


class XpEventPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    multiplier: float = Field(2.0, gt=0, le=20)
    starts_at: datetime
    ends_at: datetime
    action_filter: Optional[str] = Field(None, max_length=500)
    enabled: bool = True


class XpEventUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    multiplier: Optional[float] = Field(None, gt=0, le=20)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    action_filter: Optional[str] = Field(None, max_length=500)
    enabled: Optional[bool] = None


@router.get("")
async def list_xp_events(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    return {"items": await svc.list_events(db)}


@router.post("")
async def create_xp_event(
    body: XpEventPayload,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    if body.ends_at <= body.starts_at:
        raise HTTPException(400, "ends_at must be after starts_at")
    return await svc.create_event(db, body.model_dump())


@router.put("/{event_id}")
async def update_xp_event(
    event_id: int,
    body: XpEventUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    payload = {k: v for k, v in body.model_dump().items() if v is not None or k in ("description", "action_filter")}
    try:
        result = await svc.update_event(db, event_id, payload)
    except ValueError as e:
        raise HTTPException(400, "ends_at must be after starts_at") from e
    if result is None:
        raise HTTPException(404, "Event not found")
    return result


@router.delete("/{event_id}")
async def delete_xp_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    if not await svc.delete_event(db, event_id):
        raise HTTPException(404, "Event not found")
    return {"ok": True}
