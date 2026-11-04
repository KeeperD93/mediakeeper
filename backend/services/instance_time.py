"""Time zone of the instance: where a day, an hour and a month start for its players.

Saved in the settings table and read on every use: the web process and the
background worker are separate, so neither can keep it in memory. Without a
saved zone everything stays in UTC.
"""
import asyncio
import logging
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from sqlalchemy.ext.asyncio import AsyncSession

from services.settings import get_setting

logger = logging.getLogger("mediakeeper.instance_time")

INSTANCE_TIMEZONE_KEY = "system.timezone"
# In the time zone database, but no place anyone would pick.
_UNLISTED_ZONES = frozenset({"Factory", "localtime"})
_DAYS_COMPARED = 366


@lru_cache(maxsize=1)
def _load_zones() -> dict[str, ZoneInfo]:
    """Every zone to choose from, kept loaded: their offsets are read on each request."""
    return {name: ZoneInfo(name) for name in available_timezones() - _UNLISTED_ZONES}


async def is_known_zone(name: str) -> bool:
    """Whether ``name`` can be chosen. Walks the disk on the first call only."""
    return name in await asyncio.to_thread(_load_zones)


def _offset_minutes(moment: datetime, zone: tzinfo) -> int:
    return int(moment.astimezone(zone).utcoffset().total_seconds() // 60)


@lru_cache(maxsize=1)
def _zone_groups(day: date) -> list[dict]:
    """Zones that count days alike: the same offset on each day of the coming year.

    Only these can share a row of the list, as two zones with the same offset today can
    part ways in summer. UTC stays alone, as the reference. ``offset`` is that of ``day``,
    in minutes, smallest first. Reads every zone for a year, hence once a day.
    """
    noon = datetime.combine(day, time(12), tzinfo=UTC)
    moments = [noon + timedelta(days=count) for count in range(_DAYS_COMPARED)]
    alike: dict[tuple[int, ...], list[str]] = defaultdict(list)
    for name, zone in _load_zones().items():
        if name != "UTC":
            alike[tuple(_offset_minutes(moment, zone) for moment in moments)].append(name)
    groups = [{"offset": offsets[0], "zones": sorted(names)} for offsets, names in alike.items()]
    groups.append({"offset": 0, "zones": ["UTC"]})
    return sorted(groups, key=lambda group: group["offset"])


@lru_cache(maxsize=8)
def _load_zone(name: str) -> tzinfo:
    """``name`` as a zone, or UTC when this server cannot load it (backup restored elsewhere)."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        logger.warning("[TIMEZONE] saved zone %s cannot be loaded, using UTC: %s", name, exc)
        return UTC


async def get_instance_zone(db: AsyncSession) -> tzinfo:
    """The saved zone, or UTC when the admin has not chosen one."""
    name = await get_setting(db, INSTANCE_TIMEZONE_KEY)
    return _load_zone(name) if name else UTC


def zone_is_chosen(zone: tzinfo) -> bool:
    """Whether ``zone`` is a saved one: the fallback is the UTC constant, a saved UTC a ZoneInfo."""
    return zone is not UTC


def to_local(moment: datetime | None, zone: tzinfo) -> datetime | None:
    """``moment`` on the clock of ``zone``. A naive value is UTC: SQLite drops the offset."""
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    try:
        return moment.astimezone(zone)
    except OverflowError:
        # A date at the edge of the calendar (year 1, from an import) cannot shift.
        return moment


async def get_timezone_status(db: AsyncSession) -> dict:
    """Payload of the settings page: what is saved, what is in use, what can be chosen.

    Offsets come from here and not from the browser: its time zone data can be older,
    and these are the offsets the days and hours are counted with.
    """
    saved = await get_setting(db, INSTANCE_TIMEZONE_KEY)
    zone = _load_zone(saved) if saved else UTC
    return {
        "timezone": saved or None,
        "effective": getattr(zone, "key", "UTC"),
        "groups": await asyncio.to_thread(_zone_groups, datetime.now(UTC).date()),
    }
