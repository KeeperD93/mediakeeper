"""A ZIP puts the settings back as they were; what belongs to the installation stays."""
import json
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.user import User
from services import tmdb
from services.backup import restore as restore_module
from services.backup._state import RETENTION_DAYS_KEY
from services.backup.restore import SETTINGS_KEPT_ON_RESTORE, BackupRestoreError
from services.emby import config as emby_config
from services.feedback import KEY_RETENTION
from services.portal import dns_cache
from services.portal.gdpr import purge_pending_deletions
from services.settings import get_setting, get_user_preferences, get_watchlist_data, set_setting
from services.watchlist_scanner import _state as watchlist_state

ARCHIVE_SETTINGS = {"restore.key": "after"}
GDPR_ON = {"gdpr.enabled": "true", "gdpr.account_purge_delay_days": "30"}


def _archive(folder: Path, settings: dict, **parts: list) -> Path:
    path = folder / "restore.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("settings.json", json.dumps(settings))
        for part, data in parts.items():
            zf.writestr(f"{part}.json", json.dumps(data))
    return path


async def _restore(db, path: Path, **components):
    return await restore_module.restore_backup(db, path, components={"settings": True, **components})


@pytest.mark.asyncio
async def test_a_setting_missing_from_the_archive_goes_back_to_its_default(db_session, workspace_tmp_path):
    await set_setting(db_session, "restore.key", "before")
    await set_setting(db_session, "network.dns_cache_enabled", "true")
    await set_setting(db_session, "system.update_check_enabled", "false")

    results = await _restore(db_session, _archive(workspace_tmp_path, ARCHIVE_SETTINGS))

    assert results["settings"] == "ok"
    assert await get_setting(db_session, "restore.key") == "after"
    assert await get_setting(db_session, "network.dns_cache_enabled") == ""
    assert await get_setting(db_session, "system.update_check_enabled") == ""


@pytest.mark.asyncio
async def test_a_single_json_file_removes_nothing(db_session):
    await set_setting(db_session, "restore.key", "before")
    await set_setting(db_session, "emby.url", "http://emby.test")

    results = await restore_module.restore_json_backup(db_session, ARCHIVE_SETTINGS)

    assert results["settings"] == "ok"
    assert await get_setting(db_session, "restore.key") == "after"
    assert await get_setting(db_session, "emby.url") == "http://emby.test"


@pytest.mark.asyncio
@pytest.mark.parametrize("key", sorted(SETTINGS_KEPT_ON_RESTORE))
@pytest.mark.parametrize("in_archive", [True, False])
async def test_what_belongs_to_the_installation_stays(db_session, workspace_tmp_path, key, in_archive):
    await set_setting(db_session, key, "now")
    settings = {**ARCHIVE_SETTINGS, **({key: "old"} if in_archive else {})}

    await _restore(db_session, _archive(workspace_tmp_path, settings))

    assert await get_setting(db_session, key) == "now"
    assert await get_setting(db_session, "restore.key") == "after"


@pytest.mark.asyncio
async def test_a_single_json_file_leaves_what_belongs_to_the_installation(db_session):
    await set_setting(db_session, "notifications.last_emby_date", "now")

    await restore_module.restore_json_backup(
        db_session, {**ARCHIVE_SETTINGS, "notifications.last_emby_date": "old"},
    )

    assert await get_setting(db_session, "notifications.last_emby_date") == "now"


def test_how_long_things_are_kept_stays_out_of_a_restore():
    assert {RETENTION_DAYS_KEY, KEY_RETENTION, "chat.retention_days"} <= SETTINGS_KEPT_ON_RESTORE


async def _add_overdue_deletion(db_session) -> int:
    """Alice asked for deletion; its deadline has passed."""
    past = datetime.now(UTC) - timedelta(days=10)
    alice = User(
        username="alice", hashed_password="x", is_active=True,
        deletion_requested_at=past - timedelta(days=30), pending_deletion_at=past,
    )
    db_session.add(alice)
    await db_session.commit()
    return alice.id


@pytest.mark.asyncio
@pytest.mark.parametrize("single_file", [False, True])
async def test_turning_gdpr_back_on_gives_a_frozen_deletion_a_fresh_delay(db_session, workspace_tmp_path, single_file):
    await _add_overdue_deletion(db_session)
    await set_setting(db_session, "gdpr.enabled", "false")

    if single_file:
        await restore_module.restore_json_backup(db_session, GDPR_ON)
    else:
        await _restore(db_session, _archive(workspace_tmp_path, GDPR_ON))

    assert await purge_pending_deletions(db_session) == 0


@pytest.mark.asyncio
async def test_a_restore_with_gdpr_already_on_moves_no_deadline(db_session, workspace_tmp_path):
    await _add_overdue_deletion(db_session)
    await set_setting(db_session, "gdpr.enabled", "true")

    await _restore(db_session, _archive(workspace_tmp_path, GDPR_ON))

    assert await purge_pending_deletions(db_session) == 1


@pytest.mark.asyncio
async def test_a_failing_part_gives_no_fresh_delay(db_session, workspace_tmp_path):
    user_id = await _add_overdue_deletion(db_session)
    await set_setting(db_session, "gdpr.enabled", "false")
    deadline = select(User.pending_deletion_at).where(User.id == user_id)
    before = (await db_session.execute(deadline)).scalar_one()
    path = _archive(workspace_tmp_path, GDPR_ON, scheduler=[{"interval_sec": 60}])

    with pytest.raises(BackupRestoreError):
        await _restore(db_session, path, scheduler=True)

    assert (await db_session.execute(deadline)).scalar_one() == before
    assert await get_setting(db_session, "gdpr.enabled") == "false"


@pytest.mark.asyncio
async def test_an_archive_without_settings_removes_nothing(db_session, workspace_tmp_path):
    await set_setting(db_session, "emby.url", "http://emby.test")

    await _restore(db_session, _archive(workspace_tmp_path, {}))

    assert await get_setting(db_session, "emby.url") == "http://emby.test"


@pytest.mark.asyncio
async def test_a_failing_part_removes_nothing(db_session, workspace_tmp_path):
    await set_setting(db_session, "restore.key", "before")
    await set_setting(db_session, "network.dns_cache_enabled", "true")
    path = _archive(workspace_tmp_path, ARCHIVE_SETTINGS, scheduler=[{"interval_sec": 60}])

    with pytest.raises(BackupRestoreError):
        await _restore(db_session, path, scheduler=True)

    assert await get_setting(db_session, "restore.key") == "before"
    assert await get_setting(db_session, "network.dns_cache_enabled") == "true"


@pytest.mark.asyncio
async def test_settings_held_in_memory_follow_the_restore(db_session, workspace_tmp_path):
    await set_setting(db_session, "network.dns_cache_enabled", "true")
    await dns_cache.refresh_from_settings(db_session)
    assert dns_cache.is_enabled()
    try:
        with (
            patch("core.app_startup.apply_debug_level") as debug_level,
            patch("services.media_manager.load_categories", new=AsyncMock()) as categories,
            patch("services.portal.image_cache.refresh_enabled_flag", new=AsyncMock()) as image_flag,
        ):
            await _restore(db_session, _archive(workspace_tmp_path, ARCHIVE_SETTINGS))

        assert not dns_cache.is_enabled()
        debug_level.assert_called_once_with(False)
        categories.assert_awaited_once()
        image_flag.assert_awaited_once_with(db_session, force=True)
    finally:
        dns_cache.disable()


@pytest.mark.asyncio
async def test_a_restored_tmdb_key_and_emby_server_are_used_at_once(db_session, workspace_tmp_path):
    for key, value in (
        ("tmdb.api_key", "key-before"),
        ("emby.enabled", "true"),
        ("emby.url", "http://old-emby.test"),
        ("emby.api_key", "old-key"),
    ):
        await set_setting(db_session, key, value)
    tmdb.invalidate_tmdb_key_cache()
    emby_config._reset_config_cache()
    try:
        assert await tmdb._get_tmdb_key(db_session) == "key-before"
        assert await emby_config._get_emby_config(db_session) == ("http://old-emby.test", "old-key")

        await _restore(db_session, _archive(workspace_tmp_path, {
            "tmdb.api_key": "key-after",
            "emby.enabled": "true",
            "emby.url": "http://new-emby.test",
            "emby.api_key": "new-key",
        }))

        assert await tmdb._get_tmdb_key(db_session) == "key-after"
        assert await emby_config._get_emby_config(db_session) == ("http://new-emby.test", "new-key")
    finally:
        tmdb.invalidate_tmdb_key_cache()
        emby_config._reset_config_cache()


def _watchlist_scan(missing: int) -> dict:
    return {"series": [{"name": "Test Movie"}], "total_missing": missing, "total_upcoming": 0, "scan_time": 1}


@pytest.mark.asyncio
async def test_the_watchlist_screens_show_what_was_restored(db_session, workspace_tmp_path):
    watchlist_state.set_cache(_watchlist_scan(1))
    watchlist_state._calendar_cache["2026-01"] = [{"name": "Test Movie"}]
    path = _archive(
        workspace_tmp_path, ARCHIVE_SETTINGS,
        watchlist=[{"scan_key": "scan_results", "data": json.dumps(_watchlist_scan(9))}],
    )
    try:
        results = await restore_module.restore_backup(db_session, path, components={"watchlist": True})

        assert results["watchlist"] == "ok"
        assert watchlist_state.get_cache()["total_missing"] == 9
        assert not watchlist_state._calendar_cache
    finally:
        watchlist_state.set_cache(None)
        watchlist_state.invalidate_calendar_cache()


@pytest.mark.asyncio
async def test_a_failure_reloading_the_watchlist_does_not_undo_the_restore(db_session, workspace_tmp_path):
    path = _archive(
        workspace_tmp_path, ARCHIVE_SETTINGS,
        watchlist=[{"scan_key": "scan_results", "data": json.dumps(_watchlist_scan(9))}],
    )
    with patch.object(watchlist_state, "ensure_cache_loaded", new=AsyncMock(side_effect=RuntimeError("boom"))):
        results = await restore_module.restore_backup(db_session, path, components={"watchlist": True})

    assert results["watchlist"] == "ok"
    assert json.loads(await get_watchlist_data(db_session, "scan_results"))["total_missing"] == 9


@pytest.mark.asyncio
async def test_preferences_of_a_deleted_account_do_not_stop_the_restore(db_session, workspace_tmp_path):
    alice = User(username="alice", hashed_password="x", is_active=True)
    db_session.add(alice)
    await db_session.commit()
    alice_id = alice.id
    path = _archive(workspace_tmp_path, ARCHIVE_SETTINGS, preferences=[
        {"user_id": 4242, "preferences": {"theme": "dark"}},
        {"user_id": alice_id, "preferences": {"theme": "light"}},
    ])

    results = await _restore(db_session, path, preferences=True)

    assert results["preferences"] == "ok"
    assert await get_setting(db_session, "restore.key") == "after"
    assert json.loads((await get_user_preferences(db_session, alice_id)).preferences) == {"theme": "light"}
    assert await get_user_preferences(db_session, 4242) is None


@pytest.mark.asyncio
async def test_a_restore_without_settings_leaves_memory_alone(db_session, workspace_tmp_path):
    path = workspace_tmp_path / "restore.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("watchlist.json", json.dumps([{"scan_key": "scan", "data": "{}"}]))

    with patch("services.backup.restore.apply_restored_settings", new=AsyncMock()) as apply_settings:
        await restore_module.restore_backup(db_session, path, components={"watchlist": True})

    apply_settings.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_failure_in_memory_does_not_undo_the_restore(db_session, workspace_tmp_path):
    with patch(
        "services.portal.dns_cache.refresh_from_settings", new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        results = await _restore(db_session, _archive(workspace_tmp_path, ARCHIVE_SETTINGS))

    assert results["settings"] == "ok"
    assert await get_setting(db_session, "restore.key") == "after"
