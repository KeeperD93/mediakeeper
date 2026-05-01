"""/events router for the Portal module — sub-router aggregation.

Split across 2 files: _events_seasonal.py (challenges) + _events_rooms.py (cinema room).
"""
from fastapi import APIRouter

from ._events_rooms import router as _rooms_router
from ._events_seasonal import router as _seasonal_router

router = APIRouter(prefix="/events", tags=["portal-events"])
router.include_router(_seasonal_router)
router.include_router(_rooms_router)

__all__ = ["router"]
