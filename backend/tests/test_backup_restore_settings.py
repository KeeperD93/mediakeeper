"""A ZIP puts the settings back as they were; what belongs to the installation stays."""
import json
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from services.backup import restore as restore_module
from services.backup.restore import SETTINGS_KEPT_ON_RESTORE, BackupRestoreError
from services.portal import dns_cache
from services.settings import get_setting, set_setting

ARCHIVE_SETTINGS = {"restore.key": "after"}


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
async def test_a_restore_without_settings_leaves_memory_alone(db_session, workspace_tmp_path):
    path = workspace_tmp_path / "restore.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("watchlist.json", json.dumps([{"scan_key": "scan", "data": "{}"}]))

    with patch("services.backup.restore._apply_restored_settings", new=AsyncMock()) as apply_settings:
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
