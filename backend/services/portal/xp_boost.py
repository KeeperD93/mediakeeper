"""XP boost event service — load active multipliers and apply to grants."""
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.xp_boost import XpBoostEvent

logger = logging.getLogger("mediakeeper.portal.xp_boost")


async def get_active_multiplier(db: AsyncSession, action: str) -> float:
    """
    Return the combined XP multiplier currently active for a given action.
    Multiple overlapping events multiply together.
    Returns 1.0 when no events are active.
    """
    now = datetime.now(timezone.utc)
    rows = (await db.execute(
        select(XpBoostEvent).where(
            XpBoostEvent.enabled == True,  # noqa: E712
            XpBoostEvent.starts_at <= now,
            XpBoostEvent.ends_at >= now,
        )
    )).scalars().all()

    multiplier = 1.0
    for ev in rows:
        if ev.action_filter:
            allowed = {a.strip() for a in ev.action_filter.split(",") if a.strip()}
            if action not in allowed:
                continue
        multiplier *= ev.multiplier or 1.0
    return multiplier


async def list_events(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(
        select(XpBoostEvent).order_by(XpBoostEvent.starts_at.desc())
    )).scalars().all()
    now = datetime.now(timezone.utc)
    return [_serialize(ev, now) for ev in rows]


async def create_event(db: AsyncSession, payload: dict) -> dict:
    ev = XpBoostEvent(
        name=payload["name"],
        description=payload.get("description"),
        multiplier=float(payload.get("multiplier", 2.0)),
        starts_at=_parse_dt(payload["starts_at"]),
        ends_at=_parse_dt(payload["ends_at"]),
        action_filter=payload.get("action_filter") or None,
        enabled=bool(payload.get("enabled", True)),
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return _serialize(ev, datetime.now(timezone.utc))


async def update_event(db: AsyncSession, event_id: int, payload: dict) -> dict | None:
    ev = await db.get(XpBoostEvent, event_id)
    if not ev:
        return None
    for field in ("name", "description", "action_filter"):
        if field in payload:
            setattr(ev, field, payload[field] or None)
    if "multiplier" in payload:
        ev.multiplier = float(payload["multiplier"])
    if "starts_at" in payload:
        ev.starts_at = _parse_dt(payload["starts_at"])
    if "ends_at" in payload:
        ev.ends_at = _parse_dt(payload["ends_at"])
    if "enabled" in payload:
        ev.enabled = bool(payload["enabled"])
    await db.commit()
    await db.refresh(ev)
    return _serialize(ev, datetime.now(timezone.utc))


async def delete_event(db: AsyncSession, event_id: int) -> bool:
    ev = await db.get(XpBoostEvent, event_id)
    if not ev:
        return False
    await db.delete(ev)
    await db.commit()
    return True


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).rstrip("Z")
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _serialize(ev: XpBoostEvent, now: datetime) -> dict:
    is_active = (
        ev.enabled
        and ev.starts_at and ev.starts_at <= now
        and ev.ends_at and ev.ends_at >= now
    )
    return {
        "id": ev.id,
        "name": ev.name,
        "description": ev.description,
        "multiplier": ev.multiplier,
        "starts_at": ev.starts_at.isoformat() if ev.starts_at else None,
        "ends_at": ev.ends_at.isoformat() if ev.ends_at else None,
        "action_filter": ev.action_filter,
        "enabled": ev.enabled,
        "is_active": is_active,
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }
