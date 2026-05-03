"""List contributors, history, export, and admin moderation."""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
from urllib.parse import quote

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.social import (
    UserList, UserListItem, UserListContributor, UserListHistory,
    PRIVACY_COLLABORATIVE,
)
from services.portal.lists import (
    _log, _contributor_row, can_view, can_manage,
)

logger = logging.getLogger("mediakeeper.portal.lists_admin")


# ── Contributors ──

async def add_contributor(
    db: AsyncSession, list_id: int, owner_id: int, target_user_id: int,
) -> dict:
    lst = await db.get(UserList, list_id)
    if not lst or not await can_manage(lst, owner_id):
        return {"error": "forbidden"}
    if lst.privacy != PRIVACY_COLLABORATIVE:
        return {"error": "not_collaborative"}
    if target_user_id == owner_id:
        return {"error": "owner_implicit"}

    target = await db.get(User, target_user_id)
    if not target or not target.is_active:
        return {"error": "user_not_found"}

    existing = await _contributor_row(db, list_id, target_user_id)
    if existing:
        return {"success": True, "already": True}

    db.add(UserListContributor(list_id=list_id, user_id=target_user_id))
    await _log(db, list_id, owner_id, "contributor_added",
               extra={"target_user_id": target_user_id})
    await db.commit()
    return {"success": True}


async def remove_contributor(
    db: AsyncSession, list_id: int, owner_id: int, target_user_id: int,
) -> dict:
    lst = await db.get(UserList, list_id)
    if not lst or not await can_manage(lst, owner_id):
        return {"error": "forbidden"}
    await db.execute(
        delete(UserListContributor).where(
            UserListContributor.list_id == list_id,
            UserListContributor.user_id == target_user_id,
        )
    )
    await _log(db, list_id, owner_id, "contributor_removed",
               extra={"target_user_id": target_user_id})
    await db.commit()
    return {"success": True}


async def get_contributors(db: AsyncSession, list_id: int) -> list[dict]:
    rows = (await db.execute(
        select(UserListContributor, User)
        .join(User, User.id == UserListContributor.user_id)
        .where(UserListContributor.list_id == list_id)
        .order_by(UserListContributor.added_at)
    )).all()
    return [
        {
            "user_id": c.user_id,
            "username": u.username,
            "muted": c.muted,
            "added_at": c.added_at.isoformat() if c.added_at else None,
        }
        for c, u in rows
    ]


# ── History ──

async def get_history(
    db: AsyncSession, list_id: int, user_id: int, *, limit: int = 100,
) -> list[dict]:
    """Return audit log entries for a list — restricted to the owner
    and named contributors. ``can_view`` is too permissive here: it
    grants ``public_readonly`` viewers access, but the history reveals
    *who* added or removed *which* item, which is contributor metadata
    rather than published content."""
    lst = await db.get(UserList, list_id)
    if not lst:
        return []
    is_owner = lst.user_id == user_id
    is_contributor = (await _contributor_row(db, list_id, user_id)) is not None
    if not (is_owner or is_contributor):
        return []
    rows = (await db.execute(
        select(UserListHistory, User)
        .outerjoin(User, User.id == UserListHistory.user_id)
        .where(UserListHistory.list_id == list_id)
        .order_by(UserListHistory.created_at.desc())
        .limit(min(limit, 500))
    )).all()
    return [
        {
            "id": h.id, "action": h.action,
            "tmdb_id": h.tmdb_id, "media_type": h.media_type,
            "title": h.title, "extra": h.extra or {},
            "user_id": h.user_id,
            "username": u.username if u else None,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h, u in rows
    ]


# ── Export ──

_FILENAME_UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def _safe_filename(name: str | None, max_len: int = 80) -> str:
    """Strip filesystem-unsafe chars and collapse whitespace; empty-safe."""
    if not name:
        return ""
    cleaned = _FILENAME_UNSAFE.sub(" ", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:max_len].strip(" .")


def content_disposition(filename: str, *, fallback_stem: str = "download") -> str:
    """Build an RFC 5987-compliant `Content-Disposition` header so non-ASCII
    filenames (accents) survive legacy browsers and are decoded by modern ones."""
    stem, ext = os.path.splitext(filename)
    ascii_stem = stem.encode("ascii", "ignore").decode("ascii").strip() or fallback_stem
    return (
        f'attachment; filename="{ascii_stem}{ext}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )


async def export_list(
    db: AsyncSession, list_id: int, user_id: int, fmt: str = "json",
) -> dict | None:
    lst = await db.get(UserList, list_id)
    if not lst or not await can_view(db, lst, user_id):
        return None
    items = (await db.execute(
        select(UserListItem)
        .where(UserListItem.list_id == list_id)
        .order_by(UserListItem.added_at)
    )).scalars().all()

    if fmt == "csv":
        buf = io.StringIO()
        # BOM so Excel opens UTF-8 titles correctly.
        buf.write("\ufeff")
        writer = csv.writer(buf)
        writer.writerow(["title", "year", "added_at"])
        for row in items:
            writer.writerow([
                row.title or "",
                row.year if row.year else "",
                row.added_at.isoformat() if row.added_at else "",
            ])
        return {
            "content": buf.getvalue(),
            "mime": "text/csv; charset=utf-8",
            "filename": f"{_safe_filename(lst.name) or f'list-{list_id}'}.csv",
        }

    payload = {
        "list": {
            "id": lst.id, "name": lst.name,
            "privacy": lst.privacy, "content_type": lst.content_type,
            "genres": lst.genres or [],
            "description": lst.description,
            "created_at": lst.created_at.isoformat() if lst.created_at else None,
        },
        "items": [
            {
                "tmdb_id": row.tmdb_id,
                "media_type": row.media_type,
                "added_at": row.added_at.isoformat() if row.added_at else None,
            }
            for row in items
        ],
    }
    return {
        "content": json.dumps(payload, ensure_ascii=False, indent=2),
        "mime": "application/json",
        "filename": f"{_safe_filename(lst.name) or f'list-{list_id}'}.json",
    }


# ── Admin moderation ──

async def admin_undelete(
    db: AsyncSession, list_id: int, admin_id: int,
) -> dict:
    lst = await db.get(UserList, list_id)
    if not lst or not lst.is_deleted:
        return {"error": "not_found"}
    lst.is_deleted = False
    lst.deleted_at = None
    await _log(db, list_id, admin_id, "admin_undeleted")
    await db.commit()
    return {"success": True}


async def admin_hard_delete(
    db: AsyncSession, list_id: int, admin_id: int,
) -> dict:
    lst = await db.get(UserList, list_id)
    if not lst:
        return {"error": "not_found"}
    await db.execute(delete(UserList).where(UserList.id == list_id))
    await db.commit()
    logger.info("[LIST] Admin hard-deleted list %s (by user %s)", list_id, admin_id)
    return {"success": True}


async def admin_mute_owner(
    db: AsyncSession, list_id: int, admin_id: int, muted: bool,
) -> dict:
    lst = await db.get(UserList, list_id)
    if not lst:
        return {"error": "not_found"}
    lst.owner_muted = muted
    await _log(db, list_id, admin_id, "owner_muted" if muted else "owner_unmuted")
    await db.commit()
    return {"success": True, "muted": muted}


async def admin_mute_contributor(
    db: AsyncSession, list_id: int, target_user_id: int,
    admin_id: int, muted: bool,
) -> dict:
    row = await _contributor_row(db, list_id, target_user_id)
    if not row:
        return {"error": "not_found"}
    row.muted = muted
    await _log(
        db, list_id, admin_id,
        "contributor_muted" if muted else "contributor_unmuted",
        extra={"target_user_id": target_user_id},
    )
    await db.commit()
    return {"success": True, "muted": muted}
