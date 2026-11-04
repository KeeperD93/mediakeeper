"""Time zone of the instance: reading it, converting to it, and its admin endpoints."""
import logging
import re
import zoneinfo
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from models.portal.audit import AdminAuditLog
from services import instance_time
from services.instance_time import (
    INSTANCE_TIMEZONE_KEY,
    get_instance_zone,
    get_timezone_status,
    is_known_zone,
    to_local,
)
from services.settings import get_setting, set_setting

_ENDPOINT = "/api/system/timezone"
_LIST_LINES = Path(__file__).resolve().parents[2] / "frontend/src/constants/timezones.ts"


@pytest.mark.asyncio
async def test_without_a_saved_zone_everything_stays_in_utc(db_session):
    assert await get_instance_zone(db_session) is UTC


@pytest.mark.asyncio
async def test_the_saved_zone_is_used(db_session):
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    assert await get_instance_zone(db_session) == ZoneInfo("Europe/Paris")


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", ["Mars/Olympus", "../etc/passwd", "Europe"])
async def test_a_saved_zone_this_server_cannot_load_falls_back_to_utc(db_session, stored, caplog):
    instance_time._load_zone.cache_clear()
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, stored)
    with caplog.at_level(logging.WARNING, logger="mediakeeper.instance_time"):
        assert await get_instance_zone(db_session) is UTC
        assert await get_instance_zone(db_session) is UTC
    warnings = [r for r in caplog.records if r.name == "mediakeeper.instance_time"]
    assert len(warnings) == 1, "one warning per value, not one per read"


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        # Winter +1, summer +2: just after midnight in Paris, still the day before in UTC.
        (datetime(2026, 1, 15, 23, 30, tzinfo=UTC), datetime(2026, 1, 16, 0, 30)),
        (datetime(2026, 7, 15, 22, 30, tzinfo=UTC), datetime(2026, 7, 16, 0, 30)),
        # A naive value is UTC: that is what SQLite hands back.
        (datetime(2026, 1, 15, 23, 30), datetime(2026, 1, 16, 0, 30)),
    ],
)
def test_to_local_reads_the_clock_of_the_zone(moment, expected):
    assert to_local(moment, ZoneInfo("Europe/Paris")).replace(tzinfo=None) == expected


def test_to_local_keeps_a_half_hour_offset():
    local = to_local(datetime(2026, 1, 15, 18, 45, tzinfo=UTC), ZoneInfo("Asia/Kolkata"))
    assert (local.day, local.hour, local.minute) == (16, 0, 15)


def test_to_local_of_nothing_is_nothing():
    assert to_local(None, UTC) is None


def test_to_local_keeps_a_date_it_cannot_shift():
    year_1 = datetime(1, 1, 1, tzinfo=UTC)
    assert to_local(year_1, ZoneInfo("America/New_York")) == year_1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "known"),
    [
        ("Europe/Paris", True),
        ("America/New_York", True),
        ("UTC", True),
        ("Factory", False),
        ("localtime", False),
        ("Mars/Olympus", False),
    ],
)
async def test_only_real_places_can_be_chosen(name, known):
    assert await is_known_zone(name) is known


WINTER = date(2026, 1, 15)
SUMMER = date(2026, 7, 15)
# After the rule changes of 2026: the lines describe the year that follows.
_LIST_DAY = date(2026, 11, 4)


def _group_of(zone: str, day: date) -> dict:
    return next(g for g in instance_time._zone_groups(day) if zone in g["zones"])


@pytest.mark.parametrize(
    ("zone", "winter", "summer"),
    [
        ("Europe/Paris", 60, 120),
        ("America/New_York", -300, -240),
        ("Asia/Kolkata", 330, 330),
        ("Asia/Kathmandu", 345, 345),
        ("UTC", 0, 0),
    ],
)
def test_a_group_carries_the_offset_of_the_day(zone, winter, summer):
    assert _group_of(zone, WINTER)["offset"] == winter
    assert _group_of(zone, SUMMER)["offset"] == summer


@pytest.mark.parametrize(
    ("zone", "other"),
    [
        ("Europe/Paris", "Europe/Berlin"),
        ("Europe/Paris", "Europe/Madrid"),
        ("Europe/London", "Europe/Lisbon"),
        ("America/New_York", "America/Toronto"),
        ("Asia/Tokyo", "Asia/Seoul"),
    ],
)
def test_zones_that_count_days_alike_share_a_group(zone, other):
    assert other in _group_of(zone, WINTER)["zones"]


@pytest.mark.parametrize(
    ("zone", "other"),
    [
        # Same offset in January, not in July.
        ("Europe/Paris", "Africa/Lagos"),
        ("America/New_York", "America/Bogota"),
        ("America/Denver", "America/Phoenix"),
        # Same offset most of the year, a different change date.
        ("Asia/Jerusalem", "Europe/Athens"),
        ("America/New_York", "Asia/Tokyo"),
    ],
)
def test_zones_that_part_ways_during_the_year_stay_apart(zone, other):
    assert other not in _group_of(zone, WINTER)["zones"]


def _reset_zone_caches():
    ZoneInfo.clear_cache()
    # Two copies of a zone never compare equal: every kept copy goes with the cache above.
    instance_time._load_zone.cache_clear()
    instance_time._load_zones.cache_clear()
    instance_time._zone_groups.cache_clear()


@pytest.fixture
def pinned_zone_data():
    """The pinned tzdata package, not the machine's data: a country changing its rules
    must fail this when the package is bumped, not on any unrelated change."""
    zoneinfo.reset_tzpath(to=[])
    _reset_zone_caches()
    yield
    zoneinfo.reset_tzpath()
    _reset_zone_caches()


def _list_lines() -> list[list[str]]:
    lines = re.findall(r"zones: \[([^\]]+)\]", _LIST_LINES.read_text(encoding="utf-8"))
    return [re.findall(r"'([^']+)'", line) for line in lines]


@pytest.mark.usefixtures("pinned_zone_data")
def test_the_zones_of_a_line_of_the_list_count_days_alike():
    lines = _list_lines()
    assert len(lines) > 20
    for zones in lines:
        groups = [_group_of(zone, _LIST_DAY)["zones"] for zone in zones]
        assert all(group == groups[0] for group in groups), zones


@pytest.mark.usefixtures("pinned_zone_data")
def test_every_way_of_counting_days_has_a_line_of_the_list():
    """The list is the only way to choose a zone; a group on no line would show raw zone names."""
    on_a_line = {zone for zones in _list_lines() for zone in zones}
    without_a_line = [
        group["zones"]
        for group in instance_time._zone_groups(_LIST_DAY)
        if group["zones"] != ["UTC"] and not on_a_line.intersection(group["zones"])
    ]
    assert without_a_line == []


def test_groups_go_from_the_smallest_offset_to_the_largest():
    offsets = [group["offset"] for group in instance_time._zone_groups(WINTER)]
    assert offsets == sorted(offsets)
    assert offsets[0] < 0 < offsets[-1]


def test_every_zone_is_in_exactly_one_group_and_utc_is_alone():
    groups = instance_time._zone_groups(WINTER)
    names = [name for group in groups for name in group["zones"]]
    assert sorted(names) == sorted(instance_time._load_zones())
    assert {"offset": 0, "zones": ["UTC"]} in groups
    assert len(groups) < len(names) / 5, "rows must be far fewer than zones"


@pytest.mark.asyncio
async def test_status_without_a_saved_zone(db_session):
    status = await get_timezone_status(db_session)
    assert status["timezone"] is None
    assert status["effective"] == "UTC"
    assert any("Europe/Paris" in group["zones"] for group in status["groups"])


@pytest.mark.asyncio
async def test_status_of_a_saved_zone_that_cannot_be_loaded(db_session):
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Mars/Olympus")
    status = await get_timezone_status(db_session)
    assert (status["timezone"], status["effective"]) == ("Mars/Olympus", "UTC")


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["get", "put"])
async def test_endpoints_require_an_admin_session(client, method):
    response = await client.request(method, _ENDPOINT, json={"timezone": "Europe/Paris"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_endpoint_lists_the_zones(authed_client):
    response = await authed_client.get(_ENDPOINT)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["timezone"], body["effective"]) == (None, "UTC")
    tokyo = next(group for group in body["groups"] if "Asia/Tokyo" in group["zones"])
    assert tokyo["offset"] == 540


@pytest.mark.asyncio
async def test_put_endpoint_saves_the_zone_and_leaves_a_trace(authed_client, db_session):
    response = await authed_client.put(_ENDPOINT, json={"timezone": "Europe/Paris"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["timezone"], body["effective"]) == ("Europe/Paris", "Europe/Paris")
    assert await get_setting(db_session, INSTANCE_TIMEZONE_KEY) == "Europe/Paris"

    await authed_client.put(_ENDPOINT, json={"timezone": "Asia/Tokyo"})
    rows = (await db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.action == "system.timezone_changed")
        .order_by(AdminAuditLog.id)
    )).scalars().all()
    assert [row.payload for row in rows] == [
        {"from": None, "to": "Europe/Paris"},
        {"from": "Europe/Paris", "to": "Asia/Tokyo"},
    ]
    assert all(row.admin_user_id is not None for row in rows)


@pytest.mark.asyncio
async def test_saving_the_same_zone_again_leaves_no_trace(authed_client, db_session):
    await authed_client.put(_ENDPOINT, json={"timezone": "Europe/Paris"})
    response = await authed_client.put(_ENDPOINT, json={"timezone": "Europe/Paris"})
    assert response.status_code == 200, response.text
    rows = (await db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.action == "system.timezone_changed")
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value",
    ["Mars/Olympus", "europe/paris", " Europe/Paris", "Factory", "localtime", "../etc/passwd", ""],
)
async def test_put_endpoint_refuses_a_zone_outside_the_list(authed_client, db_session, value):
    response = await authed_client.put(_ENDPOINT, json={"timezone": value})
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_timezone"
    assert await get_setting(db_session, INSTANCE_TIMEZONE_KEY) == ""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"timezone": "Europe/Paris", "extra": 1},
        {"timezone": "x" * 65},
        {"timezone": None},
        {"timezone": 5},
        {},
    ],
)
async def test_put_endpoint_refuses_a_malformed_body(authed_client, db_session, payload):
    response = await authed_client.put(_ENDPOINT, json=payload)
    assert response.status_code == 422
    assert await get_setting(db_session, INSTANCE_TIMEZONE_KEY) == ""
