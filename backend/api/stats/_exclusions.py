"""Manage content excluded from stats (blacklist CLI)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.stats import add_exclusion, get_exclusions, remove_exclusion

router = APIRouter()


class ExclusionRequest(BaseModel):
    mode: str   # "exact" or "contains"
    value: str


@router.get("/exclusions")
async def list_exclusions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List content excluded from stats."""
    return await get_exclusions(db)


@router.post("/exclusions")
async def create_exclusion(
    req: ExclusionRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Add a piece of content to the stats exclusion list."""
    if req.mode not in ("exact", "contains"):
        return {"error": "mode must be 'exact' or 'contains'"}
    if not req.value.strip():
        return {"error": "value cannot be empty"}
    return await add_exclusion(db, req.mode, req.value.strip())


@router.delete("/exclusions/{index}")
async def delete_exclusion(
    index: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Remove an exclusion by index."""
    return await remove_exclusion(db, index)
