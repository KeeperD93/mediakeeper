import time
import logging
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from core.database import get_db
from services.emby import get_duplicates
from api.auth import get_current_user
from models.user import User
from models.ignored_duplicate import IgnoredDoublon
from models.duplicate_cleanup import DoublonCleanup

logger = logging.getLogger("mediakeeper.api.duplicates")
router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])

_duplicates_cache: list | None = None
_duplicates_cache_ts: float = 0
_DUPLICATES_TTL = 300


@router.get("")
async def fetch_duplicates(
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    global _duplicates_cache, _duplicates_cache_ts
    now = time.monotonic()
    if not force and _duplicates_cache is not None and (now - _duplicates_cache_ts) < _DUPLICATES_TTL:
        return _duplicates_cache
    result = await get_duplicates(db)
    _duplicates_cache = result
    _duplicates_cache_ts = now
    return result


@router.get("/count")
async def count_duplicates(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return the number of non-ignored duplicates."""
    global _duplicates_cache, _duplicates_cache_ts
    now = time.monotonic()
    if _duplicates_cache is None or (now - _duplicates_cache_ts) >= _DUPLICATES_TTL:
        _duplicates_cache = await get_duplicates(db)
        _duplicates_cache_ts = now
    all_duplicates = _duplicates_cache if isinstance(_duplicates_cache, list) else []
    # Fetch the ignored keys
    ignored_res = await db.execute(select(IgnoredDoublon.doublon_key))
    ignored_keys = {r[0] for r in ignored_res.all()}
    # Generate the key for each duplicate and filter
    # Frontend format: {id}_{number_de_sources}
    active = 0
    for d in all_duplicates:
        key = f"{d.get('id','')}_{len(d.get('sources', []))}" if isinstance(d, dict) else str(d)
        if key not in ignored_keys:
            active += 1
    return {"count": active, "total": len(all_duplicates), "ignored": len(ignored_keys)}


# ── Ignored ──

class IgnoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keys: List[Annotated[str, Field(max_length=512)]] = Field(max_length=1000)
    titles: List[Annotated[str, Field(max_length=512)]] = Field(default=[], max_length=1000)

@router.get("/ignored")
async def list_ignored(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(IgnoredDoublon).order_by(IgnoredDoublon.ignored_at.desc()))
    return [{"key": r.doublon_key, "title": r.title, "ignored_at": r.ignored_at.isoformat() if r.ignored_at else None} for r in result.scalars().all()]

@router.post("/ignored/add")
async def add_ignored(req: IgnoreRequest, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    added = 0
    for i, key in enumerate(req.keys):
        existing = await db.execute(select(IgnoredDoublon).where(IgnoredDoublon.doublon_key == key))
        if existing.scalar_one_or_none():
            continue
        title = req.titles[i] if i < len(req.titles) else None
        db.add(IgnoredDoublon(doublon_key=key, title=title))
        added += 1
    await db.commit()
    return {"success": True, "added": added}

@router.post("/ignored/remove")
async def remove_ignored(req: IgnoreRequest, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    for key in req.keys:
        await db.execute(delete(IgnoredDoublon).where(IgnoredDoublon.doublon_key == key))
    await db.commit()
    return {"success": True}


# ── Cleanup history ──

class CleanupEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(default=None, max_length=512)
    filename: Optional[str] = Field(default=None, max_length=512)
    size_bytes: int = Field(default=0, ge=0)
    action: str = Field(default="deleted", max_length=32)

class CleanupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entries: List[CleanupEntry] = Field(max_length=1000)

@router.get("/history")
async def get_history(
    limit: int = Query(50, ge=1, le=200),
    cursor: str = Query(""),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from core.pagination import decode_cursor, build_cursor_response

    query = select(DoublonCleanup).order_by(DoublonCleanup.id.desc())

    # Count total
    total_res = await db.execute(select(func.count(DoublonCleanup.id)))
    total = total_res.scalar() or 0

    # Cursor
    decoded = decode_cursor(cursor)
    if decoded and "id" in decoded:
        query = query.where(DoublonCleanup.id < decoded["id"])

    result = await db.execute(query.limit(limit + 1))
    rows = result.scalars().all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = [
        {"id": r.id, "title": r.title, "filename": r.filename, "size_bytes": r.size_bytes, "action": r.action, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]
    return build_cursor_response(items, total, limit, cursor_field="id", has_more=has_more)

@router.get("/history/stats")
async def get_history_stats(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    total_res = await db.execute(select(func.count(DoublonCleanup.id)).where(DoublonCleanup.action == "deleted"))
    size_res = await db.execute(select(func.coalesce(func.sum(DoublonCleanup.size_bytes), 0)).where(DoublonCleanup.action == "deleted"))
    return {
        "total_deleted": total_res.scalar() or 0,
        "total_bytes_freed": size_res.scalar() or 0,
    }

@router.post("/history/add")
async def add_history(req: CleanupRequest, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    for e in req.entries:
        db.add(DoublonCleanup(title=e.title, filename=e.filename, size_bytes=e.size_bytes, action=e.action))
    await db.commit()
    return {"success": True, "added": len(req.entries)}
