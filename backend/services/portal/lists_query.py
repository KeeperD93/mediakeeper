"""Read-path for user lists: get single list, user lists, public lists + serialization."""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from models.portal.social import (
    UserList, UserListItem, UserListContributor,
    PRIVACY_PUBLIC_READONLY, PRIVACY_COLLABORATIVE,
)
from models.user import User
from services.portal._display_name import resolve_display_name
from services.portal.lists import (
    DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, can_view,
)


_SORT_MAP = {
    "added_desc": UserListItem.added_at.desc(),
    "added_asc": UserListItem.added_at.asc(),
    "tmdb_asc": UserListItem.tmdb_id.asc(),
    "tmdb_desc": UserListItem.tmdb_id.desc(),
}


async def get_list(
    db: AsyncSession, list_id: int, user_id: int,
    *, include_items: bool = True,
    sort: str = "added_desc",
    page: int = 1, page_size: int = DEFAULT_PAGE_SIZE,
    lang: str = "fr",
) -> dict:
    lst = await db.get(UserList, list_id)
    if not lst or not await can_view(db, lst, user_id):
        return {"error": "not_found"}

    serialized = await _serialize_list(db, lst, user_id, lang=lang)
    if include_items:
        items, total = await _paginated_items(
            db, list_id, sort=sort, page=page, page_size=page_size,
        )
        serialized["items"] = items
        serialized["items_total"] = total
        serialized["items_page"] = page
        serialized["items_page_size"] = page_size
    return serialized


async def get_user_lists(
    db: AsyncSession, user_id: int, *, include_contributed: bool = True,
) -> list[dict]:
    """Owner lists, plus collaborative lists the user is a contributor to."""
    owned = (await db.execute(
        select(UserList)
        .where(UserList.user_id == user_id, UserList.is_deleted.is_(False))
        .order_by(UserList.sort_order)
    )).scalars().all()

    contrib_rows: list[UserList] = []
    if include_contributed:
        q = (
            select(UserList)
            .join(UserListContributor, UserListContributor.list_id == UserList.id)
            .where(
                UserListContributor.user_id == user_id,
                UserList.is_deleted.is_(False),
            )
            .order_by(UserList.updated_at.desc())
        )
        contrib_rows = (await db.execute(q)).scalars().all()

    out: list[dict] = []
    seen: set[int] = set()
    for lst in list(owned) + list(contrib_rows):
        if lst.id in seen:
            continue
        seen.add(lst.id)
        out.append(await _serialize_list(db, lst, user_id, lightweight=True))
    return out


async def get_public_lists(
    db: AsyncSession, user_id: int, *, limit: int = 50, offset: int = 0,
) -> dict:
    # Exclude lists whose owner has been soft-deleted or deactivated:
    # the owner row survives but their identifying surfaces (pseudo,
    # avatar, profile) are gated everywhere else. Public list browsing
    # must honour that boundary instead of leaking ``owner_username``.
    base = (
        select(UserList)
        .join(User, User.id == UserList.user_id)
        .join(UserProfile, UserProfile.user_id == UserList.user_id)
        .where(
            UserList.privacy.in_((PRIVACY_PUBLIC_READONLY, PRIVACY_COLLABORATIVE)),
            UserList.is_deleted.is_(False),
            User.is_active.is_(True),
            UserProfile.account_active.is_(True),
            UserProfile.deleted_at.is_(None),
        )
    )
    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0
    lists = (await db.execute(
        base.order_by(UserList.updated_at.desc()).offset(offset).limit(limit)
    )).scalars().all()
    items = [await _serialize_list(db, lst, user_id, lightweight=True) for lst in lists]
    return {"items": items, "total": total}


async def get_moderation_lists(
    db: AsyncSession, user_id: int, *, limit: int = 50, offset: int = 0,
) -> dict:
    """Admin moderation view: every public/collaborative list — INCLUDING
    soft-deleted ones and those of deactivated/purged owners — so the admin
    can restore or hard-delete them. Owner display safely falls back to the
    anonymous alias for a purged owner via ``_serialize_list``."""
    base = select(UserList).where(
        UserList.privacy.in_((PRIVACY_PUBLIC_READONLY, PRIVACY_COLLABORATIVE)),
    )
    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0
    lists = (await db.execute(
        base.order_by(UserList.updated_at.desc()).offset(offset).limit(limit)
    )).scalars().all()
    items = [await _serialize_list(db, lst, user_id, lightweight=True) for lst in lists]
    return {"items": items, "total": total}


async def _serialize_list(
    db: AsyncSession, lst: UserList, user_id: int,
    *, lightweight: bool = False, lang: str = "fr",
) -> dict:
    count = (await db.execute(
        select(func.count(UserListItem.id)).where(UserListItem.list_id == lst.id)
    )).scalar() or 0
    # Privacy boundary: expose the owner's chosen portal
    # pseudo or the localized anonymous alias — never the raw Emby
    # ``User.username``. The User row stays joined so a deleted owner
    # surfaces a NULL ``display_name`` that the helper folds into the
    # alias fallback.
    owner_row = (await db.execute(
        select(UserProfile.display_name, UserProfile.display_name_must_set)
        .where(UserProfile.user_id == lst.user_id)
    )).first()
    if owner_row is None:
        owner_display_name, owner_must_set = None, True
    else:
        owner_display_name, owner_must_set = owner_row
    preview_posters = (await db.execute(
        select(UserListItem.poster_url)
        .where(UserListItem.list_id == lst.id, UserListItem.poster_url.isnot(None))
        .order_by(UserListItem.added_at.desc())
        .limit(4)
    )).scalars().all()
    base = {
        "id": lst.id,
        "owner_id": lst.user_id,
        "owner_username": resolve_display_name(
            None if owner_must_set else owner_display_name,
            lst.user_id,
            lang,
        ),
        "is_owner": lst.user_id == user_id,
        "name": lst.name,
        "description": lst.description,
        "privacy": lst.privacy,
        "content_type": lst.content_type,
        "genres": lst.genres or [],
        "item_count": count,
        "preview_posters": list(preview_posters),
        "copy_count": lst.copy_count or 0,
        "owner_muted": lst.owner_muted,
        "is_deleted": lst.is_deleted,
        "created_at": lst.created_at.isoformat() if lst.created_at else None,
        "updated_at": lst.updated_at.isoformat() if lst.updated_at else None,
    }
    if not lightweight:
        # Late import to avoid circular dependency with lists_admin.
        from services.portal.lists_admin import get_contributors
        base["contributors"] = await get_contributors(db, lst.id, lang=lang)
    return base


async def _paginated_items(
    db: AsyncSession, list_id: int, *,
    sort: str, page: int, page_size: int,
) -> tuple[list[dict], int]:
    order = _SORT_MAP.get(sort, _SORT_MAP["added_desc"])
    page = max(page, 1)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    total = (await db.execute(
        select(func.count(UserListItem.id)).where(UserListItem.list_id == list_id)
    )).scalar() or 0
    rows = (await db.execute(
        select(UserListItem)
        .where(UserListItem.list_id == list_id)
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()
    return [
        {
            "id": r.id,
            "tmdb_id": r.tmdb_id,
            "media_type": r.media_type,
            "title": r.title,
            "poster_url": r.poster_url,
            "year": r.year,
            "added_by_user_id": r.added_by_user_id,
            "added_at": r.added_at.isoformat() if r.added_at else None,
        }
        for r in rows
    ], int(total)
