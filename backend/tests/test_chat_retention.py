"""Chat purge honours the admin-configured retention window (#176).

The background loop previously hardcoded a 365-day cutoff; it now reads
``chat.retention_days`` (0 = keep forever). These tests pin the extracted
``purge_chat_messages`` helper against the default, a custom window and the
disabled case.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from core.security import hash_password
from models.portal.chat import ChatMessage, ChatRoom
from models.settings import Setting
from models.user import User
from services.background_tasks import purge_chat_messages


async def _seed_messages(db_session, ages_days):
    user = User(
        username="chat-ret",
        hashed_password=hash_password("pw"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    room = ChatRoom(type="general", name="general")
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)

    now = datetime.now(timezone.utc)
    for d in ages_days:
        db_session.add(ChatMessage(
            room_id=room.id,
            user_id=user.id,
            content=f"m{d}",
            created_at=now - timedelta(days=d),
        ))
    await db_session.commit()


async def _count(db_session) -> int:
    return (await db_session.execute(
        select(func.count()).select_from(ChatMessage)
    )).scalar_one()


async def _set_retention(db_session, days: int):
    db_session.add(Setting(key="chat.retention_days", value=str(days)))
    await db_session.commit()


@pytest.mark.asyncio
async def test_purge_uses_default_one_year_when_unset(db_session):
    await _seed_messages(db_session, [400, 10])  # one past 365d, one recent
    removed = await purge_chat_messages(db_session)
    await db_session.commit()
    assert removed == 1
    assert await _count(db_session) == 1


@pytest.mark.asyncio
async def test_purge_respects_custom_retention(db_session):
    await _set_retention(db_session, 30)
    await _seed_messages(db_session, [60, 10])  # one past 30d, one within
    removed = await purge_chat_messages(db_session)
    await db_session.commit()
    assert removed == 1
    assert await _count(db_session) == 1


@pytest.mark.asyncio
async def test_purge_disabled_keeps_everything(db_session):
    await _set_retention(db_session, 0)
    await _seed_messages(db_session, [1000, 500, 10])
    removed = await purge_chat_messages(db_session)
    assert removed is None
    assert await _count(db_session) == 3
