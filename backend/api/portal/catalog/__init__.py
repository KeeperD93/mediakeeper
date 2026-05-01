"""
/discover router for the Requests module — sub-router aggregation.
Package split into modules (Rule 9, <= 300 lines).
"""
from fastapi import APIRouter

from . import _browse, _detail, _lists, _personal

router = APIRouter(prefix="/catalog", tags=["portal-discover"])
router.include_router(_lists.router)
router.include_router(_personal.router)
router.include_router(_detail.router)
router.include_router(_browse.router)

__all__ = ["router"]
