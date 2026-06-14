"""
API Backup & restore.
Package split into modules (<= 300 lines).
"""
from fastapi import APIRouter

from . import _crud, _directories, _restore, _retention

router = APIRouter(prefix="/api/backup", tags=["backup"])
router.include_router(_crud.router)
router.include_router(_restore.router)
router.include_router(_retention.router)
router.include_router(_directories.router)

__all__ = ["router"]
