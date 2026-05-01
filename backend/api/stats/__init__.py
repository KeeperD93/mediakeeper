"""
/api/stats router — sub-router aggregation.
Package split into modules (Rule 9, <= 300 lines).
"""
from fastapi import APIRouter

from . import _activity, _admin, _exclusions, _import, _overview, _users

router = APIRouter(prefix="/api/stats", tags=["stats"])
router.include_router(_overview.router)
router.include_router(_activity.router)
router.include_router(_users.router)
router.include_router(_import.router)
router.include_router(_exclusions.router)
router.include_router(_admin.router)

__all__ = ["router"]
