"""Hot-path admin/stats logs record ids, never the username (PII) (#381)."""
import logging

import pytest

from core.security import create_access_token


@pytest.mark.asyncio
async def test_stats_user_hide_log_omits_username(client, admin_user, caplog):
    """The stats admin-action log records the admin's id, never the username
    (Emby login = PII) on these endpoints (#381)."""
    client.cookies.set(
        "mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )
    with caplog.at_level(logging.INFO, logger="mediakeeper.api.stats"):
        resp = await client.post("/api/stats/users/emby-target-xyz/hide")

    assert resp.status_code == 200, resp.text
    hide_records = [r for r in caplog.records if "hidden by" in r.getMessage()]
    assert hide_records, "expected a hide log line"
    msg = hide_records[0].getMessage()
    assert admin_user.username not in msg
    assert str(admin_user.id) in msg
