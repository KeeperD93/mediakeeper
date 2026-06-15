"""Admin-editable release tags applied by the cleanName auto-search regex.

GET    /api/media/release-tags        → {"tags": [...], "defaults": [...]}
PUT    /api/media/release-tags        body {"tags": [...]} → {"tags": cleaned}
POST   /api/media/release-tags/reset  → {"tags": defaults}
"""
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.media_manager import (
    DEFAULT_RELEASE_TAGS,
    get_release_tags,
    reset_release_tags,
    set_release_tags,
)

router = APIRouter()


class ReleaseTagsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tags: List[str] = []


@router.get("/release-tags")
async def list_release_tags(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return {
        "tags": await get_release_tags(db),
        "defaults": list(DEFAULT_RELEASE_TAGS),
    }


@router.put("/release-tags")
async def update_release_tags(
    payload: ReleaseTagsPayload,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return {"tags": await set_release_tags(db, payload.tags)}


@router.post("/release-tags/reset")
async def reset_release_tags_endpoint(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return {"tags": await reset_release_tags(db)}
