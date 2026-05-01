from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from api.auth import get_current_user
from models.user import User
from models.seen_alert import SeenAlert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/seen")
async def get_seen_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the list of alert_id already marked as 'Read' by the current user."""
    result = await db.execute(
        select(SeenAlert.alert_id).where(SeenAlert.user_id == current_user.id)
    )
    return {"seen": [row for row in result.scalars().all()]}


@router.post("/seen/{alert_id}")
async def mark_alert_seen(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an alert as read for the current user."""
    # Check if already marked
    result = await db.execute(
        select(SeenAlert).where(
            SeenAlert.user_id == current_user.id,
            SeenAlert.alert_id == alert_id,
        )
    )
    if not result.scalar_one_or_none():
        db.add(SeenAlert(user_id=current_user.id, alert_id=alert_id))
        await db.commit()
    return {"success": True, "alert_id": alert_id}
