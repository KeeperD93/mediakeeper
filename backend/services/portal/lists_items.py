"""User-list item operations: add, remove, move, copy items + copy a full list."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.url_safety import safe_url
from models.portal.social import (
    UserList, UserListItem, PRIVACY_COLLABORATIVE, PRIVACY_PRIVATE,
)
from services.portal import strip_tags_and_trim
from services.portal.lists import (
    MAX_ITEMS_PER_LIST, MAX_NAME_LEN,
    can_view, can_edit_items, _log, _rate_limited,
)

# Mirrors the CSP ``img-src`` whitelist so the persisted poster URL can
# always be rendered without bumping into the page's content policy.
_POSTER_ALLOWED_HOSTS = ("image.tmdb.org", "i.imgur.com")

logger = logging.getLogger("mediakeeper.portal.lists_items")


async def add_items(
    db: AsyncSession, list_id: int, user_id: int, items: list[dict],
) -> dict:
    lst = await db.get(UserList, list_id)
    if not lst:
        return {"error": "not_found"}
    allowed, reason = await can_edit_items(db, lst, user_id)
    if not allowed:
        return {"error": reason}
    if lst.privacy == PRIVACY_COLLABORATIVE and lst.user_id != user_id:
        if _rate_limited(user_id, list_id):
            return {"error": "rate_limited"}

    count_now = (await db.execute(
        select(func.count(UserListItem.id)).where(UserListItem.list_id == list_id)
    )).scalar() or 0
    room = MAX_ITEMS_PER_LIST - count_now
    if room <= 0:
        return {"error": "list_full"}
    if len(items) > room:
        items = items[:room]

    added, duplicates = 0, 0
    for raw in items:
        tmdb_id = int(raw.get("tmdb_id") or 0)
        media_type = str(raw.get("media_type") or "").strip().lower()
        if not tmdb_id or media_type not in ("movie", "tv"):
            continue
        title = strip_tags_and_trim(raw.get("title") or "", 500) or None
        poster_url = safe_url(
            raw.get("poster_url") or "",
            allowed_hosts=_POSTER_ALLOWED_HOSTS,
        )
        year_raw = raw.get("year")
        try:
            year = int(year_raw) if year_raw not in (None, "") else None
        except (TypeError, ValueError):
            year = None
        try:
            async with db.begin_nested():
                db.add(UserListItem(
                    list_id=list_id, tmdb_id=tmdb_id, media_type=media_type,
                    title=title, poster_url=poster_url, year=year,
                    added_by_user_id=user_id,
                ))
                await db.flush()
        except IntegrityError:
            # Row already exists — refresh stale metadata (legacy rows
            # added before the snapshot columns existed carry NULLs).
            existing = (await db.execute(
                select(UserListItem).where(
                    UserListItem.list_id == list_id,
                    UserListItem.tmdb_id == tmdb_id,
                    UserListItem.media_type == media_type,
                )
            )).scalar_one_or_none()
            if existing:
                if not existing.title and title:
                    existing.title = title
                if not existing.poster_url and poster_url:
                    existing.poster_url = poster_url
                if not existing.year and year:
                    existing.year = year
                await db.flush()
            duplicates += 1
            continue
        added += 1
        await _log(
            db, list_id, user_id, "added",
            tmdb_id=tmdb_id, media_type=media_type, title=title,
        )

    lst.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "added": added, "duplicates": duplicates}


async def remove_items(
    db: AsyncSession, list_id: int, user_id: int,
    items: list[dict] | None = None, item_ids: list[int] | None = None,
) -> dict:
    lst = await db.get(UserList, list_id)
    if not lst:
        return {"error": "not_found"}
    allowed, reason = await can_edit_items(db, lst, user_id)
    if not allowed:
        return {"error": reason}
    if lst.privacy == PRIVACY_COLLABORATIVE and lst.user_id != user_id:
        if _rate_limited(user_id, list_id):
            return {"error": "rate_limited"}

    to_remove: list[UserListItem] = []
    if item_ids:
        rows = (await db.execute(
            select(UserListItem).where(
                UserListItem.list_id == list_id,
                UserListItem.id.in_(item_ids),
            )
        )).scalars().all()
        to_remove.extend(rows)
    if items:
        for raw in items:
            tmdb_id = int(raw.get("tmdb_id") or 0)
            media_type = str(raw.get("media_type") or "").strip().lower()
            if not tmdb_id:
                continue
            row = (await db.execute(
                select(UserListItem).where(
                    UserListItem.list_id == list_id,
                    UserListItem.tmdb_id == tmdb_id,
                    UserListItem.media_type == media_type,
                )
            )).scalar_one_or_none()
            if row:
                to_remove.append(row)

    removed = 0
    for row in to_remove:
        await _log(
            db, list_id, user_id, "removed",
            tmdb_id=row.tmdb_id, media_type=row.media_type,
        )
        await db.delete(row)
        removed += 1
    if removed:
        lst.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "removed": removed}


async def move_items(
    db: AsyncSession, src_list_id: int, dst_list_id: int,
    user_id: int, item_ids: list[int],
) -> dict:
    if src_list_id == dst_list_id:
        return {"error": "same_list"}
    return await _copy_or_move(
        db, src_list_id, dst_list_id, user_id, item_ids, move=True,
    )


async def copy_items(
    db: AsyncSession, src_list_id: int, dst_list_id: int,
    user_id: int, item_ids: list[int],
) -> dict:
    return await _copy_or_move(
        db, src_list_id, dst_list_id, user_id, item_ids, move=False,
    )


async def _copy_or_move(
    db: AsyncSession, src_list_id: int, dst_list_id: int,
    user_id: int, item_ids: list[int], *, move: bool,
) -> dict:
    src = await db.get(UserList, src_list_id)
    dst = await db.get(UserList, dst_list_id)
    if not src or not dst:
        return {"error": "not_found"}
    if not await can_view(db, src, user_id):
        return {"error": "forbidden"}
    if move:
        allowed, reason = await can_edit_items(db, src, user_id)
        if not allowed:
            return {"error": reason}
    allowed_dst, reason_dst = await can_edit_items(db, dst, user_id)
    if not allowed_dst:
        return {"error": reason_dst}

    rows = (await db.execute(
        select(UserListItem).where(
            UserListItem.list_id == src_list_id,
            UserListItem.id.in_(item_ids),
        )
    )).scalars().all()

    added = 0
    for row in rows:
        try:
            async with db.begin_nested():
                db.add(UserListItem(
                    list_id=dst_list_id,
                    tmdb_id=row.tmdb_id, media_type=row.media_type,
                    title=row.title, poster_url=row.poster_url, year=row.year,
                    added_by_user_id=user_id,
                ))
                await db.flush()
            added += 1
            await _log(
                db, dst_list_id, user_id, "added",
                tmdb_id=row.tmdb_id, media_type=row.media_type,
                extra={"source_list_id": src_list_id},
            )
        except IntegrityError:
            continue
        if move:
            await _log(
                db, src_list_id, user_id, "removed",
                tmdb_id=row.tmdb_id, media_type=row.media_type,
            )
            await db.delete(row)

    now = datetime.now(timezone.utc)
    dst.updated_at = now
    if move:
        src.updated_at = now
    await db.commit()
    return {"success": True, "added": added}


async def copy_list(
    db: AsyncSession, source_id: int, user_id: int,
    new_name: str | None = None,
) -> dict:
    src = await db.get(UserList, source_id)
    if not src or not await can_view(db, src, user_id):
        return {"error": "not_found"}
    if src.privacy == PRIVACY_PRIVATE and src.user_id != user_id:
        return {"error": "forbidden"}

    name = strip_tags_and_trim(new_name or src.name, MAX_NAME_LEN) or src.name
    new_list = UserList(
        user_id=user_id, name=name, description=src.description,
        privacy=PRIVACY_PRIVATE, content_type=src.content_type,
        genres=src.genres,
    )
    db.add(new_list)
    await db.flush()

    items = (await db.execute(
        select(UserListItem).where(UserListItem.list_id == source_id)
    )).scalars().all()
    for row in items:
        db.add(UserListItem(
            list_id=new_list.id,
            tmdb_id=row.tmdb_id, media_type=row.media_type,
            title=row.title, poster_url=row.poster_url, year=row.year,
            added_by_user_id=user_id,
        ))

    await _log(db, new_list.id, user_id, "created",
               extra={"copied_from": source_id})
    await _log(db, source_id, user_id, "copied",
               extra={"copy_list_id": new_list.id})
    src.copy_count = (src.copy_count or 0) + 1
    await db.commit()
    await db.refresh(new_list)
    return {
        "success": True,
        "id": new_list.id,
        "items_copied": len(items),
        "source_owner_id": src.user_id if src.user_id != user_id else None,
        "source_list_id": source_id,
    }
