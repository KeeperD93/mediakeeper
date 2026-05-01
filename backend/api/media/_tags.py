"""Endpoints for category tags (persistent TMDB badges)."""
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.settings import get_setting, set_setting

router = APIRouter()


class TagsRequest(BaseModel):
    tags: dict  # {filename: {label, color, cat}}


@router.get("/tags")
async def get_tags(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return all stored category tags."""
    raw = await get_setting(db, "media.tags")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


@router.post("/tags")
async def save_tags(
    req: TagsRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Save/update the category tags (merges with existing data)."""
    raw = await get_setting(db, "media.tags")
    existing = {}
    if raw:
        try:
            existing = json.loads(raw)
        except Exception:
            pass
    existing.update(req.tags)
    await set_setting(db, "media.tags", json.dumps(existing))
    return {"success": True, "count": len(existing)}
