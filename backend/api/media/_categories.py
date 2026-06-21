"""Endpoints for dynamic media category management."""
import logging
import re as _re
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.media_manager import get_categories, save_categories

from ._helpers import _confine_browse_path

logger = logging.getLogger("mediakeeper.api.media")
router = APIRouter()


class CategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    path: str


@router.get("/categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return the list of media categories."""
    return await get_categories(db)


@router.post("/categories")
async def add_category(
    req: CategoryRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Add a new media category."""
    label = req.label.strip()
    path = req.path.strip()
    if not label or not path:
        return {"error": "name_and_path_required"}
    # Confine the user path to an allowed media root (realpath + prefix check)
    # before any filesystem access reads it.
    confined = _confine_browse_path(path)
    if confined is None:
        return {"error": "path_outside_allowed_zones"}
    target = Path(confined)
    if not target.is_dir():
        return {"error": "path_must_be_existing_directory"}
    key = _re.sub(r'[^a-z0-9]+', '', label.lower().replace(' ', ''))
    if not key:
        return {"error": "invalid_name"}
    cats = await get_categories(db)
    if any(c["key"] == key for c in cats):
        return {"error": f"category_already_exists: {label}"}
    cats.append({"key": key, "label": label, "path": str(target)})
    await save_categories(db, cats)
    logger.info("Category added: %s → %s by %s", label, target, _.username)
    return {"ok": True, "categories": cats}


@router.delete("/categories/{cat_key}")
async def remove_category(
    cat_key: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete a media category."""
    cats = await get_categories(db)
    new_cats = [c for c in cats if c["key"] != cat_key]
    if len(new_cats) == len(cats):
        return {"error": "category_not_found"}
    await save_categories(db, new_cats)
    logger.info("Category deleted: %s by %s", cat_key, _.username)
    return {"ok": True, "categories": new_cats}
