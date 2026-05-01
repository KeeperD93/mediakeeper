"""
/api/subtitles router — sub-router aggregation.
Package split into modules (Rule 9, <= 300 lines).
"""
from fastapi import APIRouter

from . import _batch, _discovery, _library, _profiles, _search, _tools

router = APIRouter(prefix="/api/subtitles", tags=["subtitles"])
router.include_router(_library.router)
router.include_router(_search.router)
router.include_router(_discovery.router)
router.include_router(_profiles.router)
router.include_router(_tools.router)
router.include_router(_batch.router)

__all__ = ["router"]
