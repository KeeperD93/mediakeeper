"""Tests for les helpers settings (new tables)."""

import json
import pytest
from sqlalchemy import select

from core.encryption import ENCRYPTED_PREFIX
from models.notification_channels import NotificationChannel
from services.settings import (
    get_setting, set_setting,
    get_settings_map, set_settings_map,
    get_user_preferences, upsert_user_preferences,
    get_watchlist_data, set_watchlist_data,
    get_notification_channel, set_notification_channel,
)


@pytest.mark.asyncio
async def test_get_set_setting(db_session):
    """get_setting/set_setting sur la table settings classique."""
    val = await get_setting(db_session, "test.key")
    assert val == ""

    await set_setting(db_session, "test.key", "hello")
    val = await get_setting(db_session, "test.key")
    assert val == "hello"

    # Update
    await set_setting(db_session, "test.key", "world")
    val = await get_setting(db_session, "test.key")
    assert val == "world"


@pytest.mark.asyncio
async def test_get_set_settings_map(db_session):
    """Bulk accesses must read/write several settings at once."""
    await set_settings_map(db_session, {
        "bulk.one": "1",
        "bulk.two": "2",
    })

    values = await get_settings_map(db_session, ["bulk.one", "bulk.two", "bulk.missing"])

    assert values == {
        "bulk.one": "1",
        "bulk.two": "2",
        "bulk.missing": "",
    }


@pytest.mark.asyncio
async def test_user_preferences(db_session, admin_user):
    """upsert/get user_preferences."""
    row = await get_user_preferences(db_session, admin_user.id)
    assert row is None

    await upsert_user_preferences(db_session, admin_user.id, preferences='{"theme":"dark"}')
    row = await get_user_preferences(db_session, admin_user.id)
    assert row is not None
    assert json.loads(row.preferences)["theme"] == "dark"

    # Update layout without touching preferences
    await upsert_user_preferences(db_session, admin_user.id, dashboard_layout='{"hidden":[]}')
    row = await get_user_preferences(db_session, admin_user.id)
    assert json.loads(row.preferences)["theme"] == "dark"
    assert json.loads(row.dashboard_layout)["hidden"] == []


@pytest.mark.asyncio
async def test_watchlist_data(db_session):
    """get/set watchlist_scans."""
    val = await get_watchlist_data(db_session, "scan_results")
    assert val == ""

    await set_watchlist_data(db_session, "scan_results", '{"series":[]}')
    val = await get_watchlist_data(db_session, "scan_results")
    assert json.loads(val)["series"] == []


@pytest.mark.asyncio
async def test_notification_channel(db_session):
    """get/set notification_channels."""
    val = await get_notification_channel(db_session, "discord")
    assert val == ""

    await set_notification_channel(
        db_session,
        "discord",
        '{"enabled":true,"webhooks":[{"url":"https://discord.com/api/webhooks/demo"}]}',
    )
    stored = (
        await db_session.execute(
            select(NotificationChannel.data).where(NotificationChannel.channel_key == "discord")
        )
    ).scalar_one()
    assert stored.startswith(ENCRYPTED_PREFIX)
    assert "discord.com/api/webhooks/demo" not in stored

    val = await get_notification_channel(db_session, "discord")
    assert json.loads(val)["enabled"] is True
