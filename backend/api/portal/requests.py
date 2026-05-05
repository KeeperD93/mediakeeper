"""Portal media request endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import require_admin, require_permission
from services.portal import requests as req_svc
from services.portal.admin import get_portal_flag

router = APIRouter(prefix="/requests", tags=["portal-requests"])


class CreateRequest(BaseModel):
    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    title: str = Field(..., min_length=1, max_length=500)
    year: Optional[int] = None
    poster_url: Optional[str] = Field(None, max_length=500)
    backdrop_url: Optional[str] = Field(None, max_length=500)
    requested_seasons: Optional[list] = None
    on_behalf_of: Optional[int] = None


class StatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected|available)$")
    reason: Optional[str] = Field(None, max_length=500)


@router.get("")
async def list_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    cursor: Optional[str] = None,
    limit: int = Query(25, ge=1, le=100),
    up: tuple[User, UserProfile] = Depends(require_permission("can_portal")),
    db: AsyncSession = Depends(get_db),
):
    return await req_svc.list_requests(
        db,
        status_filter,
        cursor,
        limit,
        include_sensitive=False,
    )


@router.get("/admin")
async def list_requests_admin(
    status_filter: Optional[str] = Query(None, alias="status"),
    cursor: Optional[str] = None,
    limit: int = Query(25, ge=1, le=100),
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await req_svc.list_requests(
        db,
        status_filter,
        cursor,
        limit,
        include_sensitive=True,
    )


class BatchStatusQuery(BaseModel):
    tmdb_ids: list[int]


@router.post("/batch-status")
async def batch_status(
    data: BatchStatusQuery,
    up: tuple[User, UserProfile] = Depends(require_permission("can_portal")),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the **global** request status for a list of TMDB IDs.

    Used by the portal to mark cards as already requested ("post-it"
    badge + greyed-out request button) regardless of which user filed
    the request — the rule is global, no double-requesting.

    When the admin has enabled ``anonymize_requests`` in the Portal
    settings, the ``requested_by`` field is stripped from the response
    for non-admin users so nobody can tell who filed a given request.
    Admins keep access to the username so they can moderate.

    Response: { "<tmdb_id>": { "status": "pending"|"approved"|"rejected"|"available",
                               "requested_at": "...", "requested_by"?: "pseudo" } }
    Missing tmdb_ids are simply omitted from the result.
    """
    if not data.tmdb_ids:
        return {"results": {}}

    user, profile = up
    is_admin = profile.role == "admin"
    anonymize = False
    if not is_admin:
        anonymize = await get_portal_flag(db, "portal.anonymize_requests")

    import logging
    logging.getLogger("mediakeeper.portal.requests").info(
        f"[BATCH_STATUS] user={user.username!r} role={profile.role!r} "
        f"is_admin={is_admin} anonymize={anonymize} tmdb_ids={len(data.tmdb_ids)}"
    )

    return {"results": await req_svc.get_batch_status(
        db, data.tmdb_ids, anonymize=anonymize,
    )}


@router.post("")
async def create_request(
    data: CreateRequest,
    up: tuple[User, UserProfile] = Depends(require_permission("can_portal")),
    db: AsyncSession = Depends(get_db),
):
    user, profile = up
    req_data = data.model_dump()

    # Admin creating on behalf of a user
    if data.on_behalf_of and profile.role == "admin":
        target_user_id = data.on_behalf_of
        req_data["requested_by_admin"] = user.id
    else:
        target_user_id = user.id

    is_admin = profile.role == "admin"
    result = await req_svc.create_request(db, target_user_id, req_data, is_admin=is_admin)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Grant XP for creating a request (capped at 5/day by the XP service)
    try:
        from services.portal.xp import grant_xp
        req_id = result.get("id") or result.get("request_id") or "unknown"
        await grant_xp(db, target_user_id, "request_created", str(req_id))
    except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
        pass  # XP is best-effort, never blocks the request

    return result


@router.post("/{request_id}/vote")
async def vote_request(
    request_id: int,
    up: tuple[User, UserProfile] = Depends(require_permission("can_portal")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await req_svc.vote_request(db, request_id, user.id)
    if "error" in result:
        if result["error"] == "votes_disabled":
            raise HTTPException(status_code=410, detail=result["error"])
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.put("/{request_id}/status")
async def update_status(
    request_id: int,
    data: StatusUpdate,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user, _ = admin
    result = await req_svc.update_request_status(
        db, request_id, data.status, user.id, data.reason
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/{request_id}")
async def delete_request_endpoint(
    request_id: int,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: hard-delete a request (row removed entirely, not just rejected)."""
    result = await req_svc.delete_request(db, request_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/quota")
async def get_quota(
    up: tuple[User, UserProfile] = Depends(require_permission("can_portal")),
    db: AsyncSession = Depends(get_db),
):
    user, profile = up
    result = await req_svc.get_user_quota(db, user.id)
    if profile.role == "admin":
        result["unlimited"] = True
    return result


@router.get("/admin/blacklist")
async def list_blacklist_endpoint(
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List media auto-blocked after reaching 3 rejections. Admin-only."""
    from services.portal.requests_blacklist import list_blacklist
    return {"items": await list_blacklist(db)}


@router.delete("/admin/blacklist/{blacklist_id}")
async def unblock_blacklist_endpoint(
    blacklist_id: int,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Unblock a blacklisted media so users can request it again."""
    from services.portal.requests_blacklist import unblock_media
    result = await unblock_media(db, blacklist_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
