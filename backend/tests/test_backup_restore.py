import json
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.security import create_access_token
from services.backup import restore as restore_module
from services.backup.restore import (
    ENCRYPTION_KEY_ARCHIVE_NAME,
    BackupRestoreError,
)
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
async def test_restore_reports_embedded_key_without_writing_it(
    db_session, workspace_tmp_path, tmp_path, monkeypatch,
):
    """Restoration must surface the embedded key for manual recovery and
    must never touch the live key file on its own."""
    backup_path = Path(workspace_tmp_path) / "with_key.zip"
    fake_key = "definitely-not-a-real-fernet-key-but-good-enough-for-tests"
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("settings.json", json.dumps({"restore.key": "after"}))
        zf.writestr(ENCRYPTION_KEY_ARCHIVE_NAME, fake_key)
        zf.writestr(
            "manifest.json",
            json.dumps(
                {
                    "version": "1.1",
                    "encryption_key": {
                        "status": "included",
                        "source": "env",
                        "archive_path": ENCRYPTION_KEY_ARCHIVE_NAME,
                    },
                }
            ),
        )

    target_key_file = tmp_path / "encryption_key"
    monkeypatch.setattr(
        "core.encryption._KEY_FILE_PATHS",
        (target_key_file,),
    )

    results = await restore_module.restore_backup(
        db_session,
        backup_path,
        components={"settings": True},
    )

    assert results["settings"] == "ok"
    assert "encryption_key" in results
    assert results["encryption_key"]["status"] == "present"
    assert results["encryption_key"]["source"] == "env"
    assert results["encryption_key"]["archive_path"] == ENCRYPTION_KEY_ARCHIVE_NAME
    assert "Manual recovery required" in results["encryption_key"]["hint"]
    # The Fernet key must never be written automatically — operator-only.
    assert not target_key_file.exists()


@pytest.mark.asyncio
async def test_restore_signals_missing_key_with_recovery_hint(
    db_session, workspace_tmp_path,
):
    backup_path = Path(workspace_tmp_path) / "no_key.zip"
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("settings.json", json.dumps({"restore.key": "after"}))
        zf.writestr(
            "manifest.json",
            json.dumps(
                {
                    "version": "1.1",
                    "encryption_key": {
                        "status": "absent",
                        "source": None,
                        "archive_path": None,
                    },
                }
            ),
        )

    results = await restore_module.restore_backup(
        db_session,
        backup_path,
        components={"settings": True},
    )

    assert results["settings"] == "ok"
    assert results["encryption_key"]["status"] == "absent"
    assert results["encryption_key"]["archive_path"] is None
    assert "No encryption key" in results["encryption_key"]["hint"]


@pytest.mark.asyncio
async def test_restore_endpoint_returns_error_on_partial_restore(client, admin_user):
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    with patch(
        "api.backup._restore._validate_uploaded_backup_archive",
        return_value=None,
    ), patch(
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
