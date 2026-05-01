"""User lists core — access control, rate limiting, audit log, list CRUD.

Items, bulk operations, copy, export, contributors and admin moderation
live in ``lists_items`` and ``lists_admin`` — this module keeps the
primitives the other two layers build on.

Privacy model:
- ``private``          — only the owner sees and edits.
- ``public_readonly``  — anyone can view and copy, only the owner edits.
- ``collaborative``    — opt-in contributors can add/remove in addition to
                         the owner. Item history is per contributor.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.social import (
    UserList, UserListContributor, UserListHistory,
    VALID_PRIVACY, VALID_CONTENT_TYPES,
    PRIVACY_PRIVATE, PRIVACY_PUBLIC_READONLY, PRIVACY_COLLABORATIVE,
)
from services.portal import sanitize

logger = logging.getLogger("mediakeeper.portal.lists")

MAX_NAME_LEN = 200
MAX_DESCRIPTION_LEN = 1000
MAX_ITEMS_PER_LIST = 5000
MAX_GENRES = 20
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500
COLLAB_EDIT_WINDOW_SECONDS = 60
COLLAB_EDIT_MAX_PER_WINDOW = 30


# ── Validation helpers ──

def _normalize_privacy(raw: str | None) -> str:
    if raw in VALID_PRIVACY:
        return raw
    return PRIVACY_PRIVATE


def _normalize_content_type(raw: str | None) -> str:
    if raw in VALID_CONTENT_TYPES:
        return raw
    return "mixed"


def _normalize_genres(raw: Any) -> list[str] | None:
    if not raw or not isinstance(raw, list):
        return None
    cleaned = [str(g).strip().lower() for g in raw if str(g).strip()]
    return cleaned[:MAX_GENRES] if cleaned else None


# ── Access control ──

async def _contributor_row(
    db: AsyncSession, list_id: int, user_id: int,
) -> UserListContributor | None:
    result = await db.execute(
        select(UserListContributor).where(
            UserListContributor.list_id == list_id,
            UserListContributor.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def can_view(db: AsyncSession, lst: UserList, user_id: int) -> bool:
    if lst.is_deleted:
        return False
    if lst.user_id == user_id:
        return True
    if lst.privacy in (PRIVACY_PUBLIC_READONLY, PRIVACY_COLLABORATIVE):
        return True
    return False


async def can_edit_items(
    db: AsyncSession, lst: UserList, user_id: int,
) -> tuple[bool, str | None]:
    if lst.is_deleted:
        return False, "list_deleted"
    if lst.user_id == user_id:
        return (False, "owner_muted") if lst.owner_muted else (True, None)
    if lst.privacy != PRIVACY_COLLABORATIVE:
        return False, "forbidden"
    contrib = await _contributor_row(db, lst.id, user_id)
    if not contrib:
        return False, "not_contributor"
    if contrib.muted:
        return False, "contributor_muted"
    return True, None


async def can_manage(lst: UserList, user_id: int) -> bool:
    """Only the owner (un-muted, not soft-deleted) can rename / change privacy / delete."""
    return lst.user_id == user_id and not lst.owner_muted and not lst.is_deleted


# ── Rate limiting (in-memory, per-process) ──

_rl_bucket: dict[tuple[int, int], list[datetime]] = {}


def _rate_limited(user_id: int, list_id: int) -> bool:
    now = datetime.now(timezone.utc)
    key = (user_id, list_id)
    cutoff = now - timedelta(seconds=COLLAB_EDIT_WINDOW_SECONDS)
    bucket = [t for t in _rl_bucket.get(key, []) if t > cutoff]
    if len(bucket) >= COLLAB_EDIT_MAX_PER_WINDOW:
        _rl_bucket[key] = bucket
        return True
    bucket.append(now)
    _rl_bucket[key] = bucket
    return False


# ── Audit log ──

async def _log(
    db: AsyncSession, list_id: int, user_id: int | None, action: str,
    *, tmdb_id: int | None = None, media_type: str | None = None,
    title: str | None = None, extra: dict | None = None,
) -> None:
    db.add(UserListHistory(
        list_id=list_id, user_id=user_id, action=action,
        tmdb_id=tmdb_id, media_type=media_type, title=title, extra=extra,
    ))


# ── CRUD ──

async def create_list(db: AsyncSession, user_id: int, data: dict) -> dict:
    name = sanitize(data.get("name", ""), MAX_NAME_LEN)
    if not name:
        return {"error": "name_required"}
    lst = UserList(
        user_id=user_id,
        name=name,
        description=sanitize(data.get("description", ""), MAX_DESCRIPTION_LEN) or None,
        privacy=_normalize_privacy(data.get("privacy")),
        content_type=_normalize_content_type(data.get("content_type")),
        genres=_normalize_genres(data.get("genres")),
    )
    db.add(lst)
    await db.flush()
    await _log(db, lst.id, user_id, "created",
               extra={"privacy": lst.privacy, "content_type": lst.content_type})
    await db.commit()
    await db.refresh(lst)
    return {"success": True, "id": lst.id}


async def update_list(
    db: AsyncSession, list_id: int, user_id: int, data: dict,
) -> dict:
    lst = await db.get(UserList, list_id)
    if not lst:
        return {"error": "not_found"}
    if not await can_manage(lst, user_id):
        return {"error": "forbidden"}

    changes: dict[str, Any] = {}
    if "name" in data:
        new_name = sanitize(data["name"], MAX_NAME_LEN)
        if new_name and new_name != lst.name:
            changes["name"] = {"from": lst.name, "to": new_name}
            lst.name = new_name
    if "description" in data:
        new_desc = sanitize(data["description"] or "", MAX_DESCRIPTION_LEN) or None
        if new_desc != lst.description:
            changes["description"] = True
            lst.description = new_desc
    if "privacy" in data:
        new_privacy = _normalize_privacy(data["privacy"])
        if new_privacy != lst.privacy:
            changes["privacy"] = {"from": lst.privacy, "to": new_privacy}
            lst.privacy = new_privacy
    if "content_type" in data:
        new_ct = _normalize_content_type(data["content_type"])
        if new_ct != lst.content_type:
            changes["content_type"] = {"from": lst.content_type, "to": new_ct}
            lst.content_type = new_ct
    if "genres" in data:
        new_genres = _normalize_genres(data["genres"])
        if new_genres != lst.genres:
            changes["genres"] = True
            lst.genres = new_genres

    if changes:
        await _log(db, lst.id, user_id, "updated", extra=changes)
        await db.commit()
    return {"success": True, "id": lst.id, "changes": list(changes.keys())}


async def delete_list(db: AsyncSession, list_id: int, user_id: int) -> dict:
    """Soft-delete (admin can undo via lists_admin.admin_undelete)."""
    lst = await db.get(UserList, list_id)
    if not lst or lst.is_deleted:
        return {"error": "not_found"}
    if not await can_manage(lst, user_id):
        return {"error": "forbidden"}
    lst.is_deleted = True
    lst.deleted_at = datetime.now(timezone.utc)
    await _log(db, lst.id, user_id, "deleted")
    await db.commit()
    return {"success": True}


# Read-path helpers live in ``lists_query`` to keep this module under the
# 300-line ceiling; see ``get_list``, ``get_user_lists``, ``get_public_lists``.
