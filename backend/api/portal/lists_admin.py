"""Admin moderation endpoints for user lists.

Mounted under ``/api/portal/admin/lists``. Gated by ``require_admin``.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import require_admin
from services.portal import lists_admin as svc_admin

router = APIRouter(prefix="/admin/lists", tags=["portal-lists-admin"])


class MuteToggle(BaseModel):
    muted: bool


def _http_error(result: dict) -> None:
    err = result.get("error") if isinstance(result, dict) else None
    if not err:
        return
    status = {"not_found": 404, "forbidden": 403}.get(err, 400)
    raise HTTPException(status_code=status, detail=err)


@router.post("/{list_id}/undelete")
async def admin_undelete(
    list_id: int,
    up: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    admin_user, _ = up
    result = await svc_admin.admin_undelete(db, list_id, admin_user.id)
    _http_error(result)
    return result


@router.delete("/{list_id}")
async def admin_hard_delete(
    list_id: int,
    up: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    admin_user, _ = up
    result = await svc_admin.admin_hard_delete(db, list_id, admin_user.id)
    _http_error(result)
    return result


@router.post("/{list_id}/mute-owner")
async def admin_mute_owner(
    list_id: int,
    data: MuteToggle,
    up: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    admin_user, _ = up
    result = await svc_admin.admin_mute_owner(db, list_id, admin_user.id, data.muted)
    _http_error(result)
    return result


@router.post("/{list_id}/contributors/{user_id}/mute")
async def admin_mute_contributor(
    list_id: int,
    user_id: int,
    data: MuteToggle,
    up: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    admin_user, _ = up
    result = await svc_admin.admin_mute_contributor(
        db, list_id, user_id, admin_user.id, data.muted,
    )
    _http_error(result)
    return result
