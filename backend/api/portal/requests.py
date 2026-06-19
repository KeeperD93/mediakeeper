"""Portal media request endpoints."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.url_safety import safe_url
from core.i18n import get_request_locale
from core.rate_limit import limiter, portal_user_or_ip_key
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import require_admin, require_permission
from services.portal import requests as req_svc
from services.portal.achievements import safe_check_all_achievements_in_new_session
from services.portal.admin import get_portal_flag

router = APIRouter(prefix="/requests", tags=["portal-requests"])


class CreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    title: str = Field(..., min_length=1, max_length=500)
    year: Optional[int] = None
    poster_url: Optional[str] = Field(None, max_length=500)
    backdrop_url: Optional[str] = Field(None, max_length=500)
    requested_seasons: Optional[list] = Field(default=None, max_length=100)
    on_behalf_of: Optional[int] = None

    # Drop any non-http(s) image URL before it is stored and re-served to
    # the community list / admin queue (background-image / <img src> sinks).
    @field_validator("poster_url", "backdrop_url")
    @classmethod
    def _safe_image_url(cls, v: Optional[str]) -> Optional[str]:
        return safe_url(v, schemes={"http", "https"})


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(..., pattern="^(approved|rejected|available)$")
    reason: Optional[str] = Field(None, max_length=500)


@router.get("")
async def list_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    cursor: Optional[str] = None,
    limit: int = Query(25, ge=1, le=100),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(require_permission("can_portal")),
    db: AsyncSession = Depends(get_db),
):
    return await req_svc.list_requests(
        db,
        status_filter,
        cursor,
        limit,
        include_sensitive=False,
        locale=locale,
    )


@router.get("/admin")
async def list_requests_admin(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    sort: str = Query("recent", pattern="^(recent|oldest|title)$"),
    media_type: Optional[str] = Query(None, alias="type", pattern="^(movie|tv)$"),
    locale: str = Depends(get_request_locale),
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Admin queue: offset pagination + server-side sort/filter so the
    # toolbar acts on the whole set, not just the loaded page.
    return await req_svc.list_requests(
        db,
        status_filter,
        limit=per_page,
        page=page,
        sort=sort,
        media_type=media_type,
        include_sensitive=True,
        locale=locale,
    )


BATCH_STATUS_MAX_IDS = 100
# Outer raw-payload guard: a multiplier of the unique cap leaves room
# for legitimate clients that submit duplicates without letting an
# absurd payload reach the dedup loop.
BATCH_STATUS_MAX_RAW_IDS = BATCH_STATUS_MAX_IDS * 10


class BatchStatusQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tmdb_ids: list[int] = Field(..., max_length=BATCH_STATUS_MAX_RAW_IDS)


def _dedupe_keep_order(ids: list[int]) -> list[int]:
    """Drop duplicate ids while preserving the original submission order."""
    seen: set[int] = set()
    out: list[int] = []
    for tid in ids:
        if tid in seen:
            continue
        seen.add(tid)
        out.append(tid)
    return out


@router.post("/batch-status")
# 3600/minute (was the global 120 default) — infinite-scroll discover fires
# one batch lookup per loaded page, so a fast browse bursts past 120. The high
# ceiling clears that while still bounding abuse (per-account scope).
@limiter.limit("3600/minute", key_func=portal_user_or_ip_key)
async def batch_status(
    data: BatchStatusQuery,
    request: Request,
    up: tuple[User, UserProfile] = Depends(require_permission("can_portal")),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the **global** request status for a list of TMDB IDs.

    Used by the portal to mark cards as already requested ("post-it"
    badge + greyed-out request button) regardless of which user filed
    the request — the rule is global, no double-requesting.

    The unique-id cap is applied **after** dedup so a client that
    legitimately repeats ids in the same payload still works as long as
    the deduplicated count stays under ``BATCH_STATUS_MAX_IDS``.

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

    unique_ids = _dedupe_keep_order(data.tmdb_ids)
    if len(unique_ids) > BATCH_STATUS_MAX_IDS:
        raise HTTPException(status_code=422, detail="too_many_tmdb_ids")

    user, profile = up
    is_admin = profile.role == "admin"
    anonymize = False
    if not is_admin:
        anonymize = await get_portal_flag(db, "portal.anonymize_requests")

    import logging
    logging.getLogger("mediakeeper.portal.requests").info(
        f"[BATCH_STATUS] user={user.username!r} role={profile.role!r} "
        f"is_admin={is_admin} anonymize={anonymize} tmdb_ids={len(unique_ids)}"
    )

    return {"results": await req_svc.get_batch_status(
        db, unique_ids, anonymize=anonymize,
    )}


@router.post("")
async def create_request(
    data: CreateRequest,
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(
        safe_check_all_achievements_in_new_session,
        target_user_id,
        None,
        "request_created",
    )
    return result


@router.put("/{request_id}/status")
async def update_status(
    request_id: int,
    data: StatusUpdate,
    background_tasks: BackgroundTasks,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user, _ = admin
    result = await req_svc.update_request_status(
        db, request_id, data.status, user.id, data.reason
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    # Status flips can unlock community trophies for the original requester
    # (e.g. ambassador on `approved`). Run in the background — the admin
    # response should not wait on it. Skip if the requester was GDPR-purged.
    requester_id = result.get("user_id")
    if requester_id is not None:
        background_tasks.add_task(
            safe_check_all_achievements_in_new_session,
            requester_id,
            None,
            "request_status_change",
        )
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
