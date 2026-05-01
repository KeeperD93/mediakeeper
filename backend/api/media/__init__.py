"""
/api/media router — sub-router aggregation.
Package split into modules (Rule 9, <= 300 lines).
"""
from fastapi import APIRouter

from . import _browse, _categories, _metadata, _move, _release_tags, _rename, _tags, _tmdb

router = APIRouter(prefix="/api/media", tags=["media"])
router.include_router(_browse.router)
router.include_router(_categories.router)
router.include_router(_tmdb.router)
router.include_router(_rename.router)
router.include_router(_move.router)
router.include_router(_tags.router)
router.include_router(_metadata.router)
router.include_router(_release_tags.router)

__all__ = ["router"]
