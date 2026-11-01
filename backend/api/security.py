"""Admin security dashboard API — read login attempts, manage blocks."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from constants.security import (
    BLOCK_REQUIRES_IP_OR_USERNAME,
    INVALID_IP,
    INVALID_SCOPE,
    SELF_BLOCK_FORBIDDEN,
    UNKNOWN_CLIENT_IP,
)
from core.database import get_db
from core.proxy import get_client_ip, normalize_ip
from models.user import User
from services.security import (
    create_block,
    list_active_blocks,
    list_recent_attempts,
    purge_old_attempts,
    release_block,
)

from api.auth import get_current_user

logger = logging.getLogger("mediakeeper.api.security")
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

    @field_validator("username", mode="before")
    @classmethod
    def _normalize_username(cls, value: object) -> object:
        # Stored in the trimmed, lower-cased form the sign-ins are matched with. Runs
        # before max_length: lower() can lengthen a name ("İ" becomes two characters).
        if isinstance(value, str):
            return value.strip().lower() or None
        return value

    @model_validator(mode="after")
    def _check_target_and_scope(self) -> "BlockRequest":
        if not self.ip and not self.username:
            raise ValueError(BLOCK_REQUIRES_IP_OR_USERNAME)
        if self.scope not in VALID_SCOPES:
            raise ValueError(INVALID_SCOPE)
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
        raise HTTPException(status_code=400, detail=INVALID_SCOPE)
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    blocked_until = payload.blocked_until
    if blocked_until and blocked_until.tzinfo is None:
        blocked_until = blocked_until.replace(tzinfo=timezone.utc)
    # A non-permanent block with no future expiry is inert (never active and
    # hidden from the list) — reject it so the operator isn't misled into
    # thinking an attacker is blocked mid-incident.
    if not payload.permanent and (
        blocked_until is None or blocked_until <= datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=400, detail="block_requires_future_expiry")
    # Refuse self-block: a block on the operator's own username or current IP
    # locks them out of the backoffice once their JWT expires (hard to recover
    # on a single-admin instance).
    if payload.username and payload.username == admin.username.lower():
        raise HTTPException(status_code=400, detail=SELF_BLOCK_FORBIDDEN)
    ip = None
    if payload.ip:
        # Stored in the canonical form sign-ins are matched with. A range or a typo
        # would never match anyone, so only an address or the unknown marker passes.
        ip = normalize_ip(payload.ip)
        if ip is None and payload.ip.strip().lower() == UNKNOWN_CLIENT_IP:
            ip = UNKNOWN_CLIENT_IP
        if ip is None:
            raise HTTPException(status_code=400, detail=INVALID_IP)
    # An operator whose own address cannot be read signs in under the unknown marker.
    if ip and ip == (get_client_ip(request) or UNKNOWN_CLIENT_IP):
        raise HTTPException(status_code=400, detail=SELF_BLOCK_FORBIDDEN)
    block_id = await create_block(
        db,
        admin_id=admin.id,
        ip=ip,
        username=payload.username,
        scope=payload.scope,
        permanent=payload.permanent,
        blocked_until=blocked_until,
        reason=payload.reason,
    )
    return {"id": block_id}


@router.delete("/blocks/{block_id}")
async def remove_block(
    block_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    released = await release_block(db, block_id)
    if released is None:
        raise HTTPException(status_code=404, detail="block_not_found")
    # The rows are gone: this line is the only trace of who lifted what.
    logger.info("[SECURITY] unblock admin_id=%s removed=%r", admin.id, released["removed"])
    return {"success": True, **released}


@router.post("/attempts/purge")
async def purge_attempts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Admin-triggered purge of the attempts older than the retention period;
    nothing schedules it."""
    deleted = await purge_old_attempts(db)
    return {"deleted": deleted}
