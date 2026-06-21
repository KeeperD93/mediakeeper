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


@pytest.mark.asyncio
async def test_stats_user_unhide_log_omits_username(client, admin_user, caplog):
    client.cookies.set(
        "mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )
    with caplog.at_level(logging.INFO, logger="mediakeeper.api.stats"):
        resp = await client.post("/api/stats/users/emby-target-xyz/unhide")
    assert resp.status_code == 200, resp.text
    recs = [r for r in caplog.records if "unhidden by" in r.getMessage()]
    assert recs, "expected an unhide log line"
    assert admin_user.username not in recs[0].getMessage()
    assert str(admin_user.id) in recs[0].getMessage()


@pytest.mark.asyncio
async def test_stats_user_delete_log_omits_username(client, admin_user, caplog):
    client.cookies.set(
        "mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )
    with caplog.at_level(logging.INFO, logger="mediakeeper.api.stats"):
        resp = await client.delete("/api/stats/users/emby-target-xyz")
    assert resp.status_code == 200, resp.text
    recs = [r for r in caplog.records if "session(s) deleted" in r.getMessage()]
    assert recs, "expected a delete log line"
    assert admin_user.username not in recs[0].getMessage()
    assert str(admin_user.id) in recs[0].getMessage()


@pytest.mark.asyncio
async def test_stats_user_merge_log_omits_username(client, admin_user, caplog):
    client.cookies.set(
        "mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )
    with caplog.at_level(logging.INFO, logger="mediakeeper.api.stats"):
        resp = await client.post(
            "/api/stats/users/emby-src-xyz/merge", json={"target_user_id": "emby-dst-xyz"},
        )
    assert resp.status_code == 200, resp.text
    recs = [r for r in caplog.records if "session(s) merged" in r.getMessage()]
    assert recs, "expected a merge log line"
    assert admin_user.username not in recs[0].getMessage()
    assert str(admin_user.id) in recs[0].getMessage()
