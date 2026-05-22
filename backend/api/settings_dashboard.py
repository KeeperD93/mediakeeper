"""Dashboard layout CRUD endpoints.

Split out of ``api/settings.py`` to keep each file under the 300-line
cap. Mounted as a sub-router of the main settings router so the URLs
stay ``/api/settings/dashboard``.
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.auth import get_current_user
from models.user import User

router = APIRouter(tags=["settings"])

DEFAULT_DASHBOARD_LAYOUT = {
    "hidden":       [],
    "positions":    {},
    "mobile_order": None,
}


class DashboardLayoutRequest(BaseModel):
    # ``extra="forbid"`` — settings is a sensitive mutation surface,
    # unknown keys must 422 rather than silently round-trip into the
    # stored JSON.
    model_config = ConfigDict(extra="forbid")

    hidden:       List[str]            = []
    positions:    dict                 = {}
    v:            int                  = 0
    # Mobile-specific ordering. ``None`` falls back to the WIDGET_REGISTRY
    # default order on the client; an explicit array means the user has
    # customised it on a phone. Stored alongside the desktop ``positions``
    # so editing on mobile never disturbs the desktop grid coordinates.
    mobile_order: Optional[List[str]]  = None


@router.get("/dashboard")
async def get_dashboard_layout(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the dashboard layout saved by the current user."""
    from services.settings import get_user_preferences
    row = await get_user_preferences(db, current_user.id)
    if not row or not row.dashboard_layout:
        return DEFAULT_DASHBOARD_LAYOUT
    try:
        return json.loads(row.dashboard_layout)
    except Exception:
        return DEFAULT_DASHBOARD_LAYOUT


@router.post("/dashboard")
async def save_dashboard_layout(
    req: DashboardLayoutRequest,
    db:  AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save the dashboard layout for the current user."""
    from services.settings import upsert_user_preferences
    await upsert_user_preferences(db, current_user.id, dashboard_layout=json.dumps(req.model_dump()))
    return {"success": True}
