"""A restore never leaves this installation with secrets it cannot read."""
import json
import logging
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from constants.backup import BACKUP_KEY_MISMATCH
from core.encryption import ENCRYPTED_PREFIX, encrypt_value
from core.security import create_access_token
from services.backup import restore as restore_module
from services.backup.restore import BackupRestoreError
from services.backup.restore_secrets import (
    BackupKeyMismatchError,
    refuse_unreadable_secrets,
)
from services.settings import get_setting, get_watchlist_data, set_setting

WORKING = "working-secret"
FOREIGN_PLAIN = "secret-of-another-install"


def _foreign() -> str:
    token = Fernet(Fernet.generate_key()).encrypt(FOREIGN_PLAIN.encode()).decode()
    return f"{ENCRYPTED_PREFIX}{token}"


def _archive(folder: Path, settings, **parts) -> Path:
    path = Path(folder) / "restore.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("settings.json", json.dumps(settings))
        for part, data in parts.items():
            zf.writestr(f"{part}.json", json.dumps(data))
    return path


async def _restore(db, path: Path, **components):
    return await restore_module.restore_backup(db, path, components=components or {"settings": True})


async def _nothing_changed(db) -> None:
    assert await get_setting(db, "emby.api_key") == WORKING
    assert await get_setting(db, "restore.key") == "before"
    assert not db.in_nested_transaction()


@pytest.fixture
async def installed(db_session):
    await set_setting(db_session, "emby.api_key", WORKING)
    await set_setting(db_session, "restore.key", "before")


@pytest.mark.asyncio
async def test_an_archive_from_another_key_changes_nothing(db_session, workspace_tmp_path, installed):
    path = _archive(workspace_tmp_path, {"emby.api_key": _foreign(), "restore.key": "after"})

    with pytest.raises(BackupKeyMismatchError):
        await _restore(db_session, path)

    await _nothing_changed(db_session)


@pytest.mark.asyncio
async def test_the_session_still_works_after_a_refusal(db_session, workspace_tmp_path, installed):
    path = _archive(workspace_tmp_path, {"emby.api_key": _foreign()})

    with pytest.raises(BackupKeyMismatchError):
        await _restore(db_session, path)

    await set_setting(db_session, "restore.key", "later")
    assert await get_setting(db_session, "restore.key") == "later"


@pytest.mark.asyncio
async def test_a_refusal_logs_no_value(db_session, workspace_tmp_path, installed, caplog):
    foreign = _foreign()
    path = _archive(workspace_tmp_path, {"emby.api_key": foreign})

    with caplog.at_level(logging.DEBUG), pytest.raises(BackupKeyMismatchError):
        await _restore(db_session, path)

    assert "restore refused" in caplog.text.lower()
    assert foreign not in caplog.text
    assert WORKING not in caplog.text


@pytest.mark.asyncio
async def test_an_own_archive_restores_its_secrets(db_session, workspace_tmp_path, installed):
    path = _archive(workspace_tmp_path, {
        "emby.api_key": encrypt_value("restored-secret"), "restore.key": "after",
    })

    results = await _restore(db_session, path)

    assert results["settings"] == "ok"
    assert await get_setting(db_session, "emby.api_key") == "restored-secret"
    assert await get_setting(db_session, "restore.key") == "after"


@pytest.mark.asyncio
async def test_an_archive_without_secrets_is_not_refused(db_session, workspace_tmp_path, installed):
    results = await _restore(db_session, _archive(workspace_tmp_path, {"restore.key": "after"}))

    assert results["settings"] == "ok"
    assert await get_setting(db_session, "restore.key") == "after"


@pytest.mark.asyncio
async def test_a_dead_value_never_replaces_a_working_secret(db_session, workspace_tmp_path, installed):
    """Own backup holding one value written under a lost key: the rest comes back."""
    await set_setting(db_session, "tmdb.api_key", "tmdb-working")
    path = _archive(workspace_tmp_path, {
        "emby.api_key": encrypt_value("restored-secret"),
        "tmdb.api_key": _foreign(),
        "restore.key": "after",
    })

    results = await _restore(db_session, path)

    assert results["settings"] == "ok"
    assert await get_setting(db_session, "tmdb.api_key") == "tmdb-working"
    assert await get_setting(db_session, "emby.api_key") == "restored-secret"
    assert await get_setting(db_session, "restore.key") == "after"


@pytest.mark.asyncio
async def test_a_dead_value_is_not_written_where_nothing_was_set(db_session, workspace_tmp_path, installed):
    path = _archive(workspace_tmp_path, {
        "emby.api_key": encrypt_value("restored-secret"), "tmdb.api_key": _foreign(),
    })

    await _restore(db_session, path)

    assert await get_setting(db_session, "tmdb.api_key") == ""


@pytest.mark.asyncio
async def test_an_unticked_settings_part_is_not_checked(db_session, workspace_tmp_path, installed):
    path = _archive(
        workspace_tmp_path, {"emby.api_key": _foreign(), "restore.key": "after"},
        watchlist=[{"scan_key": "scan_results", "data": "{}"}],
    )

    results = await _restore(db_session, path, watchlist=True)

    assert results["watchlist"] == "ok"
    assert await get_watchlist_data(db_session, "scan_results") == "{}"
    await _nothing_changed(db_session)


@pytest.mark.asyncio
async def test_a_single_json_file_is_refused_too(db_session, installed):
    with pytest.raises(BackupKeyMismatchError):
        await restore_module.restore_json_backup(db_session, {"emby.api_key": _foreign(), "restore.key": "after"})

    await _nothing_changed(db_session)


@pytest.mark.asyncio
async def test_a_single_json_file_skips_a_dead_value(db_session, installed):
    results = await restore_module.restore_json_backup(db_session, {
        "tmdb.api_key": encrypt_value("tmdb-restored"), "emby.api_key": _foreign(),
    })

    assert results["settings"] == "ok"
    assert await get_setting(db_session, "emby.api_key") == WORKING
    assert await get_setting(db_session, "tmdb.api_key") == "tmdb-restored"


@pytest.mark.asyncio
async def test_a_settings_part_that_is_no_object_stays_a_failed_restore(db_session, workspace_tmp_path):
    with pytest.raises(BackupRestoreError):
        await _restore(db_session, _archive(workspace_tmp_path, ["not", "an", "object"]))


@pytest.mark.parametrize("value", [1, None, True, ["fernet:v1:x"], {"a": "fernet:v1:x"}, ""])
def test_only_text_can_be_a_secret(value):
    refuse_unreadable_secrets([("settings", {"some.key": value}, None)])


def test_a_malformed_token_counts_as_unreadable():
    with pytest.raises(BackupKeyMismatchError):
        refuse_unreadable_secrets([("settings", {"emby.api_key": f"{ENCRYPTED_PREFIX}é"}, None)])


def _as_admin(client, admin_user) -> None:
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))


async def _assert_refused(resp, db_session) -> None:
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == BACKUP_KEY_MISMATCH
    await _nothing_changed(db_session)


@pytest.mark.asyncio
async def test_the_restore_route_answers_the_refusal(client, admin_user, db_session, workspace_tmp_path, installed):
    _as_admin(client, admin_user)
    path = _archive(workspace_tmp_path, {"emby.api_key": _foreign(), "restore.key": "after"})

    with patch("api.backup._restore.get_backup_path", return_value=path):
        resp = await client.post("/api/backup/restore", json={
            "filename": "restore.zip", "components": {"settings": True},
        })

    await _assert_refused(resp, db_session)


@pytest.mark.asyncio
async def test_the_upload_route_answers_the_refusal_and_leaves_no_file(
    client, admin_user, db_session, workspace_tmp_path, installed, monkeypatch,
):
    monkeypatch.setenv("BACKUP_PATH", str(workspace_tmp_path))
    _as_admin(client, admin_user)
    path = _archive(workspace_tmp_path, {"emby.api_key": _foreign(), "restore.key": "after"})

    resp = await client.post(
        "/api/backup/upload-restore",
        files={"file": ("backup.zip", path.read_bytes(), "application/zip")},
        data={"components": json.dumps({"settings": True})},
    )

    await _assert_refused(resp, db_session)
    assert not list(Path(workspace_tmp_path).glob("__upload_*"))


@pytest.mark.asyncio
async def test_the_json_route_answers_the_refusal(
    client, admin_user, db_session, workspace_tmp_path, installed, monkeypatch,
):
    monkeypatch.setenv("BACKUP_PATH", str(workspace_tmp_path))
    _as_admin(client, admin_user)
    body = json.dumps({"emby.api_key": _foreign(), "restore.key": "after"})

    resp = await client.post(
        "/api/backup/upload-restore-json",
        files={"file": ("settings.json", body, "application/json")},
        data={"components": json.dumps({"settings": True})},
    )

    await _assert_refused(resp, db_session)
    assert not list(Path(workspace_tmp_path).glob("__upload_*"))
