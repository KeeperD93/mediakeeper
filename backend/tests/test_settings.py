"""Tests for les helpers settings (new tables)."""

import json
import pytest
from pydantic import ValidationError
from sqlalchemy import select

from api.settings_dashboard import DashboardLayoutRequest
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
async def test_upsert_user_preferences_absorbs_first_write_race(db_session, admin_user, monkeypatch):
    """A concurrent first-save that wins the user_id unique race is adopted as
    the row to update, not surfaced as an IntegrityError (the create path uses
    a SAVEPOINT + reload)."""
    from models.user_preferences import UserPreference
    from services.settings import _kv

    # A row already exists (as if a parallel request just inserted it) but the
    # first lookup misses it, reproducing the SELECT-then-INSERT window.
    db_session.add(UserPreference(user_id=admin_user.id, preferences='{"x":1}'))
    await db_session.commit()

    real_get = _kv.get_user_preferences
    seen = {"n": 0}

    async def _missing_first(db, user_id, **kw):
        seen["n"] += 1
        return None if seen["n"] == 1 else await real_get(db, user_id, **kw)

    monkeypatch.setattr(_kv, "get_user_preferences", _missing_first)

    row = await upsert_user_preferences(db_session, admin_user.id, table_columns='{"t":[10]}')
    assert row.user_id == admin_user.id
    assert json.loads(row.table_columns)["t"] == [10]


@pytest.mark.asyncio
async def test_watchlist_data(db_session):
    """get/set watchlist_scans."""
    val = await get_watchlist_data(db_session, "scan_results")
    assert val == ""

    await set_watchlist_data(db_session, "scan_results", '{"series":[]}')
    val = await get_watchlist_data(db_session, "scan_results")
    assert json.loads(val)["series"] == []


@pytest.mark.asyncio
async def test_dashboard_layout_mobile_order_round_trip(db_session, admin_user):
    """``mobile_order`` survives the schema → JSON → DB → fetch cycle."""
    req = DashboardLayoutRequest(
        hidden=["statPlays"],
        positions={"activity": {"x": 0, "y": 0, "w": 11, "h": 30}},
        v=22,
        mobile_order=["healthScore", "activity", "heatmap"],
    )

    await upsert_user_preferences(
        db_session, admin_user.id, dashboard_layout=json.dumps(req.model_dump())
    )
    row = await get_user_preferences(db_session, admin_user.id)

    payload = json.loads(row.dashboard_layout)
    assert payload["mobile_order"] == ["healthScore", "activity", "heatmap"]
    assert payload["hidden"] == ["statPlays"]


def test_dashboard_layout_request_rejects_unknown_field():
    """``extra="forbid"`` rejects rogue keys with 422."""
    with pytest.raises(ValidationError):
        DashboardLayoutRequest(
            hidden=[],
            positions={},
            v=22,
            mobile_order=None,
            unknown_field="oops",
        )


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
