"""Endpoints for category tags (persistent TMDB badges)."""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.settings import get_setting, set_setting

router = APIRouter()

# Per-file category badges all live in one JSON setting; bound the entry
# count and key/value sizes so the row can't be grown without limit
# (admin-only, but otherwise no guard against accidental/abusive bloat).
MAX_TAGS = 20000
MAX_KEY_LENGTH = 1024
MAX_VALUE_LENGTH = 2048


class TagsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tags: dict  # {filename: category-descriptor}

    @field_validator("tags")
    @classmethod
    def _bounded(cls, value: dict) -> dict:
        if len(value) > MAX_TAGS:
            raise ValueError("too_many_tags")
        for key, val in value.items():
            if len(key) > MAX_KEY_LENGTH:
                raise ValueError("tag_key_too_long")
            if len(json.dumps(val)) > MAX_VALUE_LENGTH:
                raise ValueError("tag_value_too_large")
        return value


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
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass
    existing.update(req.tags)
    if len(existing) > MAX_TAGS:
        raise HTTPException(400, "too_many_tags")
    await set_setting(db, "media.tags", json.dumps(existing))
    return {"success": True, "count": len(existing)}
