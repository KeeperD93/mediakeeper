"""Do Not Disturb hours follow the time zone chosen for the instance."""
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.notification_engine import _common, added_media, system
from services.settings import set_setting

_RULES = {"dnd_enabled": True, "dnd_start": "23:00", "dnd_end": "07:00"}
_ITEM = {"Id": "12345", "Name": "Test Movie"}
# A container set to Europe/Paris in winter: 23:30 on its clock, 22:30 UTC.
_LATE_IN_PARIS = datetime(2026, 1, 15, 22, 30, tzinfo=UTC)


def _freeze(monkeypatch, moment: datetime, container: datetime | None = None) -> None:
    """Stop the clock at ``moment``; ``container`` is what a call without a zone reads."""

    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment.astimezone(tz) if tz else (container or moment).replace(tzinfo=None)

    monkeypatch.setattr(_common, "datetime", Frozen)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("zone", "moment", "expected"),
    [
        # 03:30 UTC is 22:30 in Toronto: still before the quiet hours there.
        ("America/Toronto", datetime(2026, 1, 15, 3, 30, tzinfo=UTC), False),
        # 14:30 UTC is 23:30 in Tokyo: already inside them there.
        ("Asia/Tokyo", datetime(2026, 1, 15, 14, 30, tzinfo=UTC), True),
    ],
)
async def test_the_hours_are_read_in_the_chosen_zone(db_session, monkeypatch, zone, moment, expected):
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, zone)
    _freeze(monkeypatch, moment)
    assert await _common._is_dnd(db_session, _RULES) is expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (datetime(2026, 1, 15, 21, 59, tzinfo=UTC), True),  # 06:59 in Tokyo
        (datetime(2026, 1, 15, 22, 1, tzinfo=UTC), False),  # 07:01 in Tokyo
        (datetime(2026, 1, 15, 13, 59, tzinfo=UTC), False),  # 22:59 in Tokyo
        (datetime(2026, 1, 15, 14, 0, tzinfo=UTC), True),  # 23:00 in Tokyo
    ],
)
async def test_hours_across_midnight_keep_their_bounds(db_session, monkeypatch, moment, expected):
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Asia/Tokyo")
    _freeze(monkeypatch, moment)
    assert await _common._is_dnd(db_session, _RULES) is expected


@pytest.mark.asyncio
async def test_without_a_chosen_zone_the_container_clock_still_applies(db_session, monkeypatch):
    _freeze(monkeypatch, _LATE_IN_PARIS, container=datetime(2026, 1, 15, 23, 30))
    assert await _common._is_dnd(db_session, _RULES) is True


@pytest.mark.asyncio
async def test_a_saved_utc_is_a_chosen_zone(db_session, monkeypatch):
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "UTC")
    _freeze(monkeypatch, _LATE_IN_PARIS, container=datetime(2026, 1, 15, 23, 30))
    assert await _common._is_dnd(db_session, _RULES) is False


@pytest.mark.asyncio
async def test_rules_turned_off_read_nothing():
    assert await _common._is_dnd(None, {"dnd_enabled": False}) is False


@pytest.fixture
def system_channels(monkeypatch):
    """A single webhook listening to the event, and a delivery that can be counted."""
    channels = {
        "discord": json.dumps({"enabled": True, "webhooks": [{"url": "x", "events": {"offline": True}}]}),
        "notif_rules": json.dumps(_RULES),
    }
    monkeypatch.setattr(system, "get_notification_channel", AsyncMock(side_effect=lambda _db, name: channels[name]))
    monkeypatch.setattr(system, "build_system_payload", AsyncMock(return_value={}))
    monkeypatch.setattr(system, "log_sent", AsyncMock())
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(system, "send_discord_webhook", send)
    return send


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("moment", "sent"),
    [
        (datetime(2026, 1, 15, 3, 30, tzinfo=UTC), 1),  # 22:30 in Toronto
        (datetime(2026, 1, 15, 4, 30, tzinfo=UTC), 0),  # 23:30 in Toronto
    ],
)
async def test_a_system_notification_waits_for_the_hours_of_the_zone(
    db_session, monkeypatch, system_channels, moment, sent,
):
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "America/Toronto")
    _freeze(monkeypatch, moment)
    await system.send_system_notification(db_session, "offline", {"name": "Test Movie"})
    assert system_channels.await_count == sent


@pytest.fixture
def media_pipeline(monkeypatch):
    """One new item ready to go; returns the delivery and the saved queue."""
    send = AsyncMock()
    save_queue = AsyncMock()
    for name, value in {
        "_load_discord_config": AsyncMock(return_value={"webhooks": [{}], "delay": 0}),
        "_get_emby_config": AsyncMock(return_value=("http://emby.test", "test-key")),
        "_load_imgur_creds": AsyncMock(return_value=("", "")),
        "_load_rules": AsyncMock(return_value=_RULES),
        "_detect_new_items": AsyncMock(return_value=[_ITEM]),
        "get_notification_channel": AsyncMock(return_value=None),
        "fetch_item_by_id": AsyncMock(return_value=_ITEM),
        "_is_item_metadata_complete": lambda _item: True,
        "_group_episodes": lambda items: items,
        "promote_grouped_items": AsyncMock(),
        "_send_item": send,
        "set_notification_channel": save_queue,
    }.items():
        monkeypatch.setattr(added_media, name, value)
    return send, save_queue


@pytest.mark.asyncio
async def test_new_media_waits_in_the_queue_during_the_hours_of_the_zone(db_session, monkeypatch, media_pipeline):
    send, save_queue = media_pipeline
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "America/Toronto")
    _freeze(monkeypatch, datetime(2026, 1, 15, 4, 30, tzinfo=UTC))
    await added_media._process_notifications(db_session)
    send.assert_not_awaited()
    assert [entry["item"]["Id"] for entry in json.loads(save_queue.await_args.args[2])] == ["12345"]


@pytest.mark.asyncio
async def test_new_media_goes_out_before_the_hours_of_the_zone(db_session, monkeypatch, media_pipeline):
    send, save_queue = media_pipeline
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "America/Toronto")
    _freeze(monkeypatch, datetime(2026, 1, 15, 3, 30, tzinfo=UTC))
    await added_media._process_notifications(db_session)
    send.assert_awaited_once()
    assert json.loads(save_queue.await_args.args[2]) == []
