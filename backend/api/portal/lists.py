"""Portal user-lists API."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_request_lang, require_permission
from services.portal import lists as svc
from services.portal import lists_items as svc_items
from services.portal import lists_admin as svc_admin
from services.portal import lists_query as svc_query
from services.portal import notifications as notif_svc

router = APIRouter(prefix="/lists", tags=["portal-lists"])


class ListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    privacy: str = Field("private", pattern="^(private|public_readonly|collaborative)$")
    content_type: str = Field("mixed", pattern="^(movies|series|documentaries|mixed)$")
    genres: Optional[list[str]] = None


class ListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    privacy: Optional[str] = Field(None, pattern="^(private|public_readonly|collaborative)$")
    content_type: Optional[str] = Field(None, pattern="^(movies|series|documentaries|mixed)$")
    genres: Optional[list[str]] = None


class ItemPayload(BaseModel):
    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    title: Optional[str] = Field(None, max_length=500)
    poster_url: Optional[str] = Field(None, max_length=500)
    year: Optional[int] = Field(None, ge=1800, le=2200)


class ItemsAdd(BaseModel):
    items: list[ItemPayload] = Field(..., min_length=1, max_length=200)


class ItemsRemove(BaseModel):
    item_ids: Optional[list[int]] = None
    items: Optional[list[ItemPayload]] = None


class ItemsMove(BaseModel):
    dst_list_id: int
    item_ids: list[int] = Field(..., min_length=1)


class CopyListRequest(BaseModel):
    new_name: Optional[str] = Field(None, max_length=200)


class ContributorPayload(BaseModel):
    user_id: int


_ERROR_STATUS = {
    "not_found": 404, "user_not_found": 404,
    "forbidden": 403, "owner_muted": 403,
    "contributor_muted": 403, "not_contributor": 403,
    "not_collaborative": 400, "owner_implicit": 400,
    "same_list": 400, "list_full": 400, "name_required": 400,
    "list_deleted": 404, "rate_limited": 429,
}


def _http_error(result: dict) -> None:
    err = result.get("error") if isinstance(result, dict) else None
    if err:
        raise HTTPException(status_code=_ERROR_STATUS.get(err, 400), detail=err)


@router.get("")
async def list_mine(
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return {"items": await svc_query.get_user_lists(db, user.id)}


@router.get("/public")
async def list_public(
    limit: int = Query(50, ge=1, le=200),
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return {"items": await svc_query.get_public_lists(db, user.id, limit=limit)}


@router.get("/{list_id}")
async def get_single(
    list_id: int,
    sort: str = Query("added_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(svc.DEFAULT_PAGE_SIZE, ge=1, le=svc.MAX_PAGE_SIZE),
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_lang),
):
    user, _ = up
    result = await svc_query.get_list(
        db, list_id, user.id,
        sort=sort, page=page, page_size=page_size, lang=lang,
    )
    _http_error(result)
    return result


@router.post("")
async def create(
    data: ListCreate,
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await svc.create_list(db, user.id, data.model_dump(exclude_unset=True))
    _http_error(result)
    return result


@router.patch("/{list_id}")
async def update(
    list_id: int,
    data: ListUpdate,
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await svc.update_list(db, list_id, user.id, data.model_dump(exclude_unset=True))
    _http_error(result)
    return result


@router.delete("/{list_id}")
async def delete(
    list_id: int,
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await svc.delete_list(db, list_id, user.id)
    _http_error(result)
    return result


@router.post("/{list_id}/items")
async def add_items(
    list_id: int,
    data: ItemsAdd,
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    payload = [p.model_dump() for p in data.items]
    result = await svc_items.add_items(db, list_id, user.id, payload)
    _http_error(result)
    return result


@router.delete("/{list_id}/items")
async def remove_items(
    list_id: int,
    data: ItemsRemove,
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    items = [p.model_dump() for p in data.items] if data.items else None
    result = await svc_items.remove_items(
        db, list_id, user.id, items=items, item_ids=data.item_ids,
    )
    _http_error(result)
    return result


@router.post("/{list_id}/move")
async def move_items(
    list_id: int,
    data: ItemsMove,
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await svc_items.move_items(
        db, list_id, data.dst_list_id, user.id, data.item_ids,
    )
    _http_error(result)
    return result


@router.post("/{list_id}/copy-items")
async def copy_items_to(
    list_id: int,
    data: ItemsMove,
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await svc_items.copy_items(
        db, list_id, data.dst_list_id, user.id, data.item_ids,
    )
    _http_error(result)
    return result


@router.post("/{list_id}/copy")
async def copy_whole_list(
    list_id: int,
    data: CopyListRequest,
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await svc_items.copy_list(db, list_id, user.id, data.new_name)
    _http_error(result)
    if result.get("source_owner_id"):
        await notif_svc.create(
            db, result["source_owner_id"], "list_copied",
            payload={
                "source_list_id": result["source_list_id"],
                "by_user_id": user.id,
            },
        )
        await db.commit()
    return result


@router.get("/{list_id}/export")
async def export_list(
    list_id: int,
    fmt: str = Query("json", pattern="^(json|csv)$"),
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await svc_admin.export_list(db, list_id, user.id, fmt=fmt)
    if not result:
        raise HTTPException(status_code=404, detail="not_found")
    return Response(
        content=result["content"],
        media_type=result["mime"],
        headers={"Content-Disposition": svc_admin.content_disposition(
            result["filename"], fallback_stem=f"list-{list_id}",
        )},
    )


@router.get("/{list_id}/history")
async def get_history(
    list_id: int,
    limit: int = Query(100, ge=1, le=500),
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return {"items": await svc_admin.get_history(db, list_id, user.id, limit=limit)}


@router.post("/{list_id}/contributors")
async def add_contributor(
    list_id: int,
    data: ContributorPayload,
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await svc_admin.add_contributor(db, list_id, user.id, data.user_id)
    _http_error(result)
    if not result.get("already"):
        await notif_svc.create(
            db, data.user_id, "list_contributor_added",
            payload={"list_id": list_id, "by_user_id": user.id},
        )
        await db.commit()
    return result


@router.delete("/{list_id}/contributors/{user_id}")
async def remove_contributor(
    list_id: int,
    user_id: int,
    up: tuple[User, UserProfile] = Depends(require_permission("can_lists")),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    result = await svc_admin.remove_contributor(db, list_id, user.id, user_id)
    _http_error(result)
    return result
