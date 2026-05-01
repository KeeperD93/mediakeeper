"""Management admin des users : hide/unhide, delete, merge."""
import json as _json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.settings import get_setting, set_setting
from models.playback_stats import PlaybackSession


async def _get_hidden_users(db: AsyncSession) -> list[str]:
    """Return the list of hidden user_id values."""
    raw = await get_setting(db, "stats.hidden_users")
    if not raw:
        return []
    try:
        return _json.loads(raw)
    except Exception:
        return []


async def _set_hidden_users(db: AsyncSession, user_ids: list[str]):
    await set_setting(db, "stats.hidden_users", _json.dumps(user_ids))


async def hide_user(db: AsyncSession, user_id: str) -> list[str]:
    hidden = await _get_hidden_users(db)
    if user_id not in hidden:
        hidden.append(user_id)
        await _set_hidden_users(db, hidden)
    return hidden


async def unhide_user(db: AsyncSession, user_id: str) -> list[str]:
    hidden = await _get_hidden_users(db)
    hidden = [uid for uid in hidden if uid != user_id]
    await _set_hidden_users(db, hidden)
    return hidden


async def delete_user_stats(db: AsyncSession, user_id: str) -> int:
    """Delete all stats for a user. Returns the number of rows removed."""
    result = await db.execute(
        PlaybackSession.__table__.delete().where(PlaybackSession.user_id == user_id)
    )
    await db.commit()
    return result.rowcount


async def merge_user_stats(db: AsyncSession, source_user_id: str, target_user_id: str) -> int:
    """Merge stats from source to target. Returns the number of sessions transferred."""
    target_name_q = select(PlaybackSession.user_name).where(
        PlaybackSession.user_id == target_user_id
    ).limit(1)
    target_name_res = await db.execute(target_name_q)
    target_row = target_name_res.first()
    target_name = target_row[0] if target_row else target_user_id

    result = await db.execute(
        PlaybackSession.__table__.update()
        .where(PlaybackSession.user_id == source_user_id)
        .values(user_id=target_user_id, user_name=target_name)
    )
    await db.commit()
    return result.rowcount
