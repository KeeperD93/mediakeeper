import json
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.security import create_access_token
from services.backup import restore as restore_module
from services.backup.restore import BackupRestoreError
from services.settings import get_setting, set_setting


@pytest.mark.asyncio
async def test_restore_backup_rolls_back_all_components_on_failure(
    monkeypatch, db_session, workspace_tmp_path,
):
    backup_path = Path(workspace_tmp_path) / "restore.zip"
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("settings.json", json.dumps({"restore.key": "after"}))
        zf.writestr("scheduler.json", json.dumps([{"key": "daily", "interval_sec": 60}]))

    await set_setting(db_session, "restore.key", "before")

    async def failing_scheduler(db, data):
        raise RuntimeError("scheduler boom")

    monkeypatch.setattr(restore_module, "_restore_scheduler", failing_scheduler)

    with pytest.raises(restore_module.BackupRestoreError):
        await restore_module.restore_backup(
            db_session,
            backup_path,
            components={"settings": True, "scheduler": True},
        )

    assert await get_setting(db_session, "restore.key") == "before"


@pytest.mark.asyncio
async def test_restore_endpoint_returns_error_on_partial_restore(client, admin_user):
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username}))

    with patch(
        "api.backup._restore.get_backup_path",
        return_value=Path("C:/fake/restore.zip"),
    ), patch(
        "api.backup._restore.restore_backup",
        new=AsyncMock(side_effect=BackupRestoreError("settings", RuntimeError("boom"), {})),
    ):
        resp = await client.post("/api/backup/restore", json={
            "filename": "restore.zip",
            "components": {"settings": True},
        })

    assert resp.status_code == 500
    assert resp.json()["detail"] == "backup_restore_failed"
