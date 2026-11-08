import io
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


def _write_settings_archive(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("settings.json", json.dumps({"restore.key": "after"}))


@pytest.mark.asyncio
@pytest.mark.parametrize("transaction_already_open", [True, False])
async def test_a_successful_restore_is_saved(db_session, workspace_tmp_path, transaction_already_open):
    """The routes read the settings first, so a transaction is open: the restore must end it.

    SQLite saves on releasing the outermost savepoint, PostgreSQL only on a commit: a
    transaction left open is the one sign of a lost restore that shows on both.
    """
    backup_path = Path(workspace_tmp_path) / "restore.zip"
    _write_settings_archive(backup_path)
    await set_setting(db_session, "restore.key", "before")
    if transaction_already_open:
        await get_setting(db_session, "restore.key")
        assert db_session.in_transaction()

    with patch.object(restore_module, "_apply_restored_settings", new=AsyncMock()):
        results = await restore_module.restore_backup(db_session, backup_path, components={"settings": True})

    assert results["settings"] == "ok"
    assert not db_session.in_transaction()
    assert await get_setting(db_session, "restore.key") == "after"


@pytest.mark.asyncio
async def test_a_successful_json_restore_is_saved(db_session):
    await set_setting(db_session, "restore.key", "before")
    await get_setting(db_session, "restore.key")

    with patch.object(restore_module, "_apply_restored_settings", new=AsyncMock()):
        results = await restore_module.restore_json_backup(db_session, {"restore.key": "after"})

    assert results["settings"] == "ok"
    assert not db_session.in_transaction()
    assert await get_setting(db_session, "restore.key") == "after"


@pytest.mark.asyncio
async def test_a_failed_restore_commits_nothing(db_session):
    await set_setting(db_session, "restore.key", "before")
    await get_setting(db_session, "restore.key")

    with patch.object(db_session, "commit", new=AsyncMock()) as commit:
        results = await restore_module.restore_json_backup(db_session, [{"scan_key": "missing-data"}])

    assert results["watchlist"].startswith("error:")
    commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_refused_commit_is_reported_as_a_failure(db_session, workspace_tmp_path):
    backup_path = Path(workspace_tmp_path) / "restore.zip"
    _write_settings_archive(backup_path)

    with (
        patch.object(db_session, "commit", new=AsyncMock(side_effect=RuntimeError("disk full"))),
        pytest.raises(BackupRestoreError),
    ):
        await restore_module.restore_backup(db_session, backup_path, components={"settings": True})


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


def _as_admin(client, admin_user):
    client.cookies.set(
        "mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )


@pytest.mark.asyncio
async def test_upload_restore_applies_the_parts_ticked_on_screen(
    client, admin_user, db_session, workspace_tmp_path, monkeypatch,
):
    """The settings screen sends its ticked parts in the upload form, next to
    the file: they must reach the restore instead of being read as none."""
    monkeypatch.setenv("BACKUP_PATH", str(workspace_tmp_path))
    _as_admin(client, admin_user)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps({"version": "1.1"}))
        zf.writestr("settings.json", json.dumps({"restore.key": "after"}))
    await set_setting(db_session, "restore.key", "before")

    resp = await client.post(
        "/api/backup/upload-restore",
        files={"file": ("backup.zip", archive.getvalue(), "application/zip")},
        data={"components": json.dumps({"settings": True})},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["results"]["settings"] == "ok"
    assert await get_setting(db_session, "restore.key") == "after"


@pytest.mark.asyncio
async def test_upload_restore_json_leaves_an_unticked_part_alone(
    client, admin_user, db_session, workspace_tmp_path, monkeypatch,
):
    monkeypatch.setenv("BACKUP_PATH", str(workspace_tmp_path))
    _as_admin(client, admin_user)
    await set_setting(db_session, "restore.key", "before")

    resp = await client.post(
        "/api/backup/upload-restore-json",
        files={"file": ("settings.json", json.dumps({"restore.key": "after"}), "application/json")},
        data={"components": json.dumps({"settings": False})},
    )

    assert resp.status_code == 200, resp.text
    assert "settings" not in resp.json()["results"]
    assert await get_setting(db_session, "restore.key") == "before"
