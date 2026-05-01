"""Seasonal events and watch parties."""
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.event import (
    SeasonalEvent, SeasonalProgress, WatchParty, WatchPartyParticipant,
)
from models.portal.chat import ChatRoom
from services.portal import sanitize

logger = logging.getLogger("mediakeeper.portal.events")


# ── Seasonal events ──

async def create_seasonal_event(
    db: AsyncSession, admin_id: int, data: dict
) -> dict:
    event = SeasonalEvent(
        name=sanitize(data["name"], 200),
        description=sanitize(data.get("description", ""), 2000),
        start_date=data["start_date"],
        end_date=data["end_date"],
        genre_filter=data.get("genre_filter"),
        target_count=data.get("target_count", 10),
        badge_id=data.get("badge_id"),
        created_by=admin_id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"success": True, "id": event.id}


async def get_active_events(db: AsyncSession) -> list[dict]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(SeasonalEvent).where(
            SeasonalEvent.start_date <= now,
            SeasonalEvent.end_date >= now,
        ).order_by(SeasonalEvent.end_date)
    )
    return [_serialize_event(e) for e in result.scalars().all()]


async def get_event_progress(
    db: AsyncSession, event_id: int, user_id: int
) -> dict:
    result = await db.execute(
        select(SeasonalProgress).where(
            SeasonalProgress.event_id == event_id,
            SeasonalProgress.user_id == user_id,
        )
    )
    sp = result.scalar_one_or_none()
    if not sp:
        return {"progress": 0, "completed": False}
    return {"progress": sp.progress, "completed": sp.completed}


async def update_event_progress(
    db: AsyncSession, event_id: int, user_id: int, increment: int = 1
) -> dict:
    event = await db.get(SeasonalEvent, event_id)
    if not event:
        return {"error": "not_found"}

    result = await db.execute(
        select(SeasonalProgress).where(
            SeasonalProgress.event_id == event_id,
            SeasonalProgress.user_id == user_id,
        )
    )
    sp = result.scalar_one_or_none()
    if not sp:
        sp = SeasonalProgress(event_id=event_id, user_id=user_id)

    sp.progress += increment
    if sp.progress >= event.target_count and not sp.completed:
        sp.completed = True
        logger.info(f"[EVENT] user_id={user_id} completed event #{event_id}")

    db.add(sp)
    await db.commit()
    return {"progress": sp.progress, "completed": sp.completed}


# ── Watch parties ──

async def create_watch_party(
    db: AsyncSession, host_id: int, data: dict
) -> dict:
    room = ChatRoom(type="party", name=sanitize(data["title"], 100))
    db.add(room)
    await db.flush()

    party = WatchParty(
        host_user_id=host_id,
        title=sanitize(data["title"], 300),
        tmdb_id=data.get("tmdb_id"),
        media_type=data.get("media_type"),
        scheduled_at=data["scheduled_at"],
        max_participants=data.get("max_participants", 20),
        chat_room_id=room.id,
    )
    db.add(party)
    await db.flush()

    db.add(WatchPartyParticipant(party_id=party.id, user_id=host_id))
    await db.commit()
    await db.refresh(party)
    return {"success": True, "id": party.id, "chat_room_id": room.id}


async def list_upcoming_parties(db: AsyncSession) -> list[dict]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(WatchParty)
        .where(WatchParty.scheduled_at >= now)
        .order_by(WatchParty.scheduled_at)
        .limit(20)
    )
    parties = result.scalars().all()
    out = []
    for p in parties:
        count = (await db.execute(
            select(func.count(WatchPartyParticipant.id))
            .where(WatchPartyParticipant.party_id == p.id)
        )).scalar() or 0
        out.append({
            "id": p.id, "title": p.title,
            "tmdb_id": p.tmdb_id, "media_type": p.media_type,
            "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
            "max_participants": p.max_participants,
            "participant_count": count,
            "host_user_id": p.host_user_id,
            "chat_room_id": p.chat_room_id,
        })
    return out


async def join_party(
    db: AsyncSession, party_id: int, user_id: int
) -> dict:
    party = await db.get(WatchParty, party_id)
    if not party:
        return {"error": "not_found"}

    count = (await db.execute(
        select(func.count(WatchPartyParticipant.id))
        .where(WatchPartyParticipant.party_id == party_id)
    )).scalar() or 0

    if count >= party.max_participants:
        return {"error": "full"}

    existing = await db.execute(
        select(WatchPartyParticipant).where(
            WatchPartyParticipant.party_id == party_id,
            WatchPartyParticipant.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"error": "already_joined"}

    db.add(WatchPartyParticipant(party_id=party_id, user_id=user_id))
    await db.commit()
    return {"success": True}


async def leave_party(
    db: AsyncSession, party_id: int, user_id: int
) -> dict:
    result = await db.execute(
        select(WatchPartyParticipant).where(
            WatchPartyParticipant.party_id == party_id,
            WatchPartyParticipant.user_id == user_id,
        )
    )
    participant = result.scalar_one_or_none()
    if participant:
        await db.delete(participant)
        await db.commit()
    return {"success": True}


def _serialize_event(e: SeasonalEvent) -> dict:
    return {
        "id": e.id, "name": e.name, "description": e.description,
        "start_date": e.start_date.isoformat() if e.start_date else None,
        "end_date": e.end_date.isoformat() if e.end_date else None,
        "genre_filter": e.genre_filter,
        "target_count": e.target_count,
        "badge_id": e.badge_id,
    }
