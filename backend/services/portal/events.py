"""Seasonal events and watch parties."""
import logging
from datetime import datetime, timezone
from sqlalchemy import case, delete, select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.event import (
    SeasonalEvent, SeasonalProgress, WatchParty, WatchPartyParticipant,
)
from models.portal.chat import ChatRoom
from services.portal import strip_tags_and_trim

logger = logging.getLogger("mediakeeper.portal.events")


# ── Seasonal events ──

async def create_seasonal_event(
    db: AsyncSession, admin_id: int, data: dict
) -> dict:
    event = SeasonalEvent(
        name=strip_tags_and_trim(data["name"], 200),
        description=strip_tags_and_trim(data.get("description", ""), 2000),
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


async def _load_seasonal_progress(
    db: AsyncSession, event_id: int, user_id: int,
) -> SeasonalProgress | None:
    """Lookup helper isolated so concurrency tests can monkeypatch it to
    drive the real INSERT path through ``uq_seasonal_progress``."""
    result = await db.execute(
        select(SeasonalProgress).where(
            SeasonalProgress.event_id == event_id,
            SeasonalProgress.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_event_progress(
    db: AsyncSession, event_id: int, user_id: int, increment: int = 1
) -> dict:
    event = await db.get(SeasonalEvent, event_id)
    if not event:
        return {"error": "not_found"}

    target_count = event.target_count
    sp = await _load_seasonal_progress(db, event_id, user_id)

    if sp is None:
        # First-time progression for this (event, user) — wrap the INSERT in
        # a SAVEPOINT so a parallel peer that beat us to the unique row only
        # invalidates the inner savepoint. The outer transaction stays
        # usable and we fall through to the atomic-increment path below.
        completed_now = increment >= target_count
        try:
            async with db.begin_nested():
                db.add(SeasonalProgress(
                    event_id=event_id,
                    user_id=user_id,
                    progress=increment,
                    completed=completed_now,
                ))
                await db.flush()
            await db.commit()
            if completed_now:
                logger.info(
                    "[EVENT] user_id=%s completed event #%s", user_id, event_id
                )
            return {"progress": increment, "completed": completed_now}
        except IntegrityError:
            logger.debug(
                "[EVENT] race avoided event_id=%s user_id=%s "
                "— concurrent insert won, falling back to atomic update",
                event_id, user_id,
            )

    # Atomic SQL increment — reading the ORM ``progress`` and writing it
    # back would silently drop a concurrent peer's bump. The keyed UPDATE
    # uses the live DB value, and the ``completed`` flag flips to True
    # the first time the post-increment count reaches ``target_count``,
    # then sticks True forever (else_ preserves the current value).
    new_progress_expr = SeasonalProgress.progress + increment
    await db.execute(
        update(SeasonalProgress)
        .where(
            SeasonalProgress.event_id == event_id,
            SeasonalProgress.user_id == user_id,
        )
        .values(
            progress=new_progress_expr,
            completed=case(
                (new_progress_expr >= target_count, True),
                else_=SeasonalProgress.completed,
            ),
        )
        .execution_options(synchronize_session=False)
    )
    await db.commit()

    fresh = (await db.execute(
        select(SeasonalProgress.progress, SeasonalProgress.completed).where(
            SeasonalProgress.event_id == event_id,
            SeasonalProgress.user_id == user_id,
        )
    )).one()
    progress = int(fresh.progress)
    completed = bool(fresh.completed)

    if completed and (progress - increment) < target_count:
        logger.info("[EVENT] user_id=%s completed event #%s", user_id, event_id)

    return {"progress": progress, "completed": completed}


# ── Watch parties ──

async def create_watch_party(
    db: AsyncSession, host_id: int, data: dict
) -> dict:
    room = ChatRoom(type="party", name=strip_tags_and_trim(data["title"], 100))
    db.add(room)
    await db.flush()

    party = WatchParty(
        host_user_id=host_id,
        title=strip_tags_and_trim(data["title"], 300),
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


async def _load_existing_participant(
    db: AsyncSession, party_id: int, user_id: int,
) -> WatchPartyParticipant | None:
    """Lookup helper isolated so concurrency tests can monkeypatch it to
    drive the real INSERT path through ``uq_party_participant``."""
    result = await db.execute(
        select(WatchPartyParticipant).where(
            WatchPartyParticipant.party_id == party_id,
            WatchPartyParticipant.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def join_party(
    db: AsyncSession, party_id: int, user_id: int
) -> dict:
    # Locking the ``WatchParty`` row serialises concurrent joins on the
    # same party so the count → cap check → INSERT trio cannot interleave
    # and let the participant table overshoot ``max_participants``. SQLite
    # accepts ``FOR UPDATE`` as a no-op; PostgreSQL actually blocks. Every
    # non-success exit below ends with an explicit ``rollback`` so the
    # ``FOR UPDATE`` row lock is released before the function returns —
    # otherwise the lock would survive on the session until its next
    # commit/close, which under load can stall every parallel join.
    party = (await db.execute(
        select(WatchParty)
        .where(WatchParty.id == party_id)
        .with_for_update()
    )).scalar_one_or_none()
    if not party:
        await db.rollback()
        return {"error": "not_found"}

    count = (await db.execute(
        select(func.count(WatchPartyParticipant.id))
        .where(WatchPartyParticipant.party_id == party_id)
    )).scalar() or 0

    if count >= party.max_participants:
        await db.rollback()
        return {"error": "full"}

    if await _load_existing_participant(db, party_id, user_id):
        await db.rollback()
        return {"error": "already_joined"}

    # SAVEPOINT belt-and-braces: even with the row lock, a parallel peer
    # racing inside a different transaction window can still trip
    # ``uq_party_participant``. The savepoint converts that into a clean
    # ``already_joined`` return without poisoning the outer session.
    try:
        async with db.begin_nested():
            db.add(WatchPartyParticipant(party_id=party_id, user_id=user_id))
            await db.flush()
    except IntegrityError:
        logger.debug(
            "[PARTY] race avoided party_id=%s user_id=%s "
            "— concurrent insert won",
            party_id, user_id,
        )
        # Savepoint is already rolled back, but the outer transaction
        # still owns the FOR UPDATE row lock — drop it before returning.
        await db.rollback()
        return {"error": "already_joined"}

    await db.commit()
    return {"success": True}


async def leave_party(
    db: AsyncSession, party_id: int, user_id: int
) -> dict:
    # Keyed DELETE is naturally idempotent: if the row vanished between a
    # caller's load and here, the statement affects 0 rows without
    # raising — unlike ``session.delete()`` on a stale instance, which can
    # surface ``StaleDataError`` on flush.
    await db.execute(
        delete(WatchPartyParticipant).where(
            WatchPartyParticipant.party_id == party_id,
            WatchPartyParticipant.user_id == user_id,
        )
    )
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
