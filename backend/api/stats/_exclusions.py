"""Manage content excluded from stats (blacklist CLI)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.stats import add_exclusion, get_exclusions, remove_exclusion

router = APIRouter()


class ExclusionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str = Field(..., pattern="^(exact|contains)$")
    value: str = Field(..., min_length=1)

    @field_validator("value")
    @classmethod
    def _non_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("value cannot be empty")
        return stripped


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
    """Add a piece of content to the stats exclusion list.

    ``mode`` and ``value`` are validated by the schema (422 on a bad mode
    or a blank value); ``value`` arrives already stripped.
    """
    return await add_exclusion(db, req.mode, req.value)


@router.delete("/exclusions")
async def delete_exclusion(
    req: ExclusionRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Remove the exclusion named by ``mode`` and ``value``, not by its position.

    Answers with the whole list, unchanged when that entry was already gone.
    """
    return await remove_exclusion(db, req.mode, req.value)
