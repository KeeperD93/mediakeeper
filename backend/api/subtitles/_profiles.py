"""Download profiles + history."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.subtitle_history import (
    get_history as svc_get_history,
    get_item_history as svc_get_item_history,
)
from services.subtitle_profiles import (
    create_profile as svc_create_profile,
    delete_profile as svc_delete_profile,
    get_profiles as svc_get_profiles,
    set_default_profile as svc_set_default,
    update_profile as svc_update_profile,
)

from ._schemas import ProfileRequest

router = APIRouter()


@router.get("/profiles")
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await svc_get_profiles(db)


@router.post("/profiles")
async def create_profile(
    req: ProfileRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await svc_create_profile(db, req.model_dump())


@router.put("/profiles/{profile_id}")
async def update_profile(
    profile_id: int,
    req: ProfileRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await svc_update_profile(db, profile_id, req.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return result


@router.delete("/profiles/{profile_id}")
async def delete_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not await svc_delete_profile(db, profile_id):
        raise HTTPException(status_code=404, detail="profile_not_found")
    return {"success": True}


@router.post("/profiles/{profile_id}/default")
async def set_default_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await svc_set_default(db, profile_id)
    if not result:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return result


@router.get("/history")
async def history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    item_id: str = Query(""),
    language: str = Query(""),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await svc_get_history(db, limit=limit, offset=offset, item_id=item_id, language=language)


@router.get("/history/{item_id}")
async def item_history(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await svc_get_item_history(db, item_id)


@router.get("/statistics")
async def statistics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from services.subtitle_history import get_statistics
    return await get_statistics(db)
