"""Chat mute helpers."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.chat import ChatMute


async def is_muted(db: AsyncSession, user_id: int) -> bool:
    """Check if user is currently muted."""
    result = await db.execute(
        select(ChatMute).where(ChatMute.user_id == user_id)
    )
    mute = result.scalar_one_or_none()
    if not mute:
        return False
    if mute.muted_until < datetime.now(timezone.utc):
        await db.delete(mute)
        await db.commit()
        return False
    return True


async def mute_user(
    db: AsyncSession, user_id: int, until: datetime, reason: str | None = None
) -> dict:
    result = await db.execute(
        select(ChatMute).where(ChatMute.user_id == user_id)
    )
    mute = result.scalar_one_or_none()
    if mute:
        mute.muted_until = until
        mute.reason = reason
    else:
        mute = ChatMute(user_id=user_id, muted_until=until, reason=reason)
    db.add(mute)
    await db.commit()
    return {"success": True}


async def unmute_user(db: AsyncSession, user_id: int) -> dict:
    result = await db.execute(
        select(ChatMute).where(ChatMute.user_id == user_id)
    )
    mute = result.scalar_one_or_none()
    if mute:
        await db.delete(mute)
        await db.commit()
    return {"success": True}
