"""Emby activity feed: alert/activity classification (real types + severity)
and UserId -> display-name resolution."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import services.emby.activity as activity
from tests._portal_profile_helpers import make_portal_user


def _item(type_, severity, user_id="", name="evt"):
    return {
        "Type": type_,
        "Severity": severity,
        "Date": "2026-01-01T00:00:00Z",
        "Name": name,
        "UserId": user_id,
        "Id": "evt-id",
    }


@pytest.mark.asyncio
async def test_alert_classification_real_types_and_severity(db_session):
    activity._reset_activity_cache()
    items = [
        _item("playback.start", "Info", "u1"),            # routine activity
        _item("user.authenticated", "Info", "u1"),        # routine activity
        _item("user.passwordchanged", "Info", "u1"),      # Info -> escalated alert
        _item("user.authenticationfailed", "Error"),      # Error -> alert via severity
    ]
    with patch.object(activity, "_get_raw_entries", new=AsyncMock(return_value=items)), \
         patch.object(activity, "_resolve_user_names", new=AsyncMock(return_value={"u1": "Alice"})):
        acts = await activity.get_activity_logs(db_session, limit=20)
        alerts = await activity.get_alerts(db_session, limit=30)
    assert {a["type"] for a in acts} == {"playback.start", "user.authenticated"}
    assert {a["type"] for a in alerts} == {"user.passwordchanged", "user.authenticationfailed"}
    activity._reset_activity_cache()


@pytest.mark.asyncio
async def test_user_resolved_from_mk_profile_then_emby_fallback(db_session):
    activity._reset_activity_cache()
    await make_portal_user(
        db_session, username="emby-act", display_name="Alice",
        role="viewer", emby_user_id="u1",
    )
    items = [
        _item("playback.start", "Info", "u1"),            # MK-linked -> Alice
        _item("playback.stop", "Info", "u2"),             # Emby-only -> Bob
        _item("plugins.pluginupdated", "Info", ""),       # system event, no UserId
    ]
    emby_user = AsyncMock(return_value={"Name": "Bob"})
    with patch.object(activity, "_get_raw_entries", new=AsyncMock(return_value=items)), \
         patch.object(activity, "get_emby_user", new=emby_user):
        acts = await activity.get_activity_logs(db_session, limit=20)
    by_type = {a["type"]: a["user"] for a in acts}
    assert by_type["playback.start"] == "Alice"   # from MK profile, no Emby call
    assert by_type["playback.stop"] == "Bob"      # from Emby fallback
    assert by_type["plugins.pluginupdated"] == ""  # system event stays user-less
    emby_user.assert_awaited_once_with(db_session, "u2")
    activity._reset_activity_cache()


@pytest.mark.asyncio
async def test_user_name_cache_avoids_repeat_emby_calls(db_session):
    activity._reset_activity_cache()
    items = [_item("playback.start", "Info", "u9")]
    emby_user = AsyncMock(return_value={"Name": "Zoe"})
    with patch.object(activity, "_get_raw_entries", new=AsyncMock(return_value=items)), \
         patch.object(activity, "get_emby_user", new=emby_user):
        first = await activity.get_activity_logs(db_session, limit=20)
        second = await activity.get_activity_logs(db_session, limit=20)
    assert first[0]["user"] == "Zoe"
    assert second[0]["user"] == "Zoe"
    emby_user.assert_awaited_once()  # second call served from cache
    activity._reset_activity_cache()
