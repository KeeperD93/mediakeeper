"""Admin security dashboard API — read login attempts, manage blocks."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from services.security import (
    create_block,
    delete_block,
    list_active_blocks,
    list_recent_attempts,
    purge_old_attempts,
)

from api.auth import get_current_user

router = APIRouter(prefix="/api/security", tags=["security"])

VALID_SCOPES = {"admin", "admin_password", "portal", "all"}


class BlockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ip: str | None = Field(default=None, max_length=64)
    username: str | None = Field(default=None, max_length=100)
    scope: str = Field(default="all")
    permanent: bool = True
    blocked_until: datetime | None = None
    reason: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _at_least_one_target(self):
        if not self.ip and not self.username:
            raise ValueError("block_requires_ip_or_username")
        if self.scope not in VALID_SCOPES:
            raise ValueError("invalid_scope")
        return self


@router.get("/attempts")
async def get_attempts(
    limit: int = Query(100, ge=1, le=500),
    scope: str | None = Query(None),
    only_failures: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if scope and scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="invalid_scope")
    return {
        "items": await list_recent_attempts(
            db, limit=limit, scope=scope, only_failures=only_failures,
        ),
    }


@router.get("/blocks")
async def get_blocks(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return {"items": await list_active_blocks(db)}


@router.post("/blocks")
async def post_block(
    payload: BlockRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    blocked_until = payload.blocked_until
    if blocked_until and blocked_until.tzinfo is None:
        blocked_until = blocked_until.replace(tzinfo=timezone.utc)
    try:
        block_id = await create_block(
            db,
            admin_id=admin.id,
            ip=payload.ip,
            username=payload.username,
            scope=payload.scope,
            permanent=payload.permanent,
            blocked_until=blocked_until,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": block_id}


@router.delete("/blocks/{block_id}")
async def remove_block(
    block_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    removed = await delete_block(db, block_id)
    if not removed:
        raise HTTPException(status_code=404, detail="block_not_found")
    return {"success": True}


@router.post("/attempts/purge")
async def purge_attempts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Admin-triggered purge. Normally runs via the scheduler."""
    deleted = await purge_old_attempts(db)
    return {"deleted": deleted}
