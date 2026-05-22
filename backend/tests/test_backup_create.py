import json
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet

from core.encryption import ENCRYPTED_PREFIX
from services.backup import DEFAULT_COMPONENTS
from services.backup.create import (
    ENCRYPTION_KEY_ARCHIVE_NAME,
    create_backup,
)
from services.settings import set_setting


@pytest.fixture
def patched_backup_dir(workspace_tmp_path, monkeypatch):
    monkeypatch.setattr(
        "services.backup.create.get_current_backup_dir",
        lambda: Path(workspace_tmp_path),
    )
    return workspace_tmp_path


@pytest.fixture
def stub_pg_dump():
    """Replace the real pg_dump subprocess with a deterministic mock so the
    backup test suite never spawns Postgres binaries in CI."""
    fake_sql = "-- mocked pg_dump --\nSELECT 1;\n"
    with patch(
        "services.backup.create._pg_dump_async",
        new=AsyncMock(return_value=fake_sql),
    ) as mocked:
        yield mocked, fake_sql


@pytest.mark.asyncio
async def test_create_backup_keeps_sensitive_settings_encrypted(
    db_session, patched_backup_dir, stub_pg_dump,
):
    await set_setting(db_session, "emby.api_key", "super-secret")
    await set_setting(db_session, "emby.url", "http://emby.local:8096")

    backup_path = await create_backup(
        db_session,
        components={
            "settings": True,
            "preferences": False,
            "scheduler": False,
            "watchlist": False,
            "logs": False,
            "pg_dump": False,
        },
    )

    with zipfile.ZipFile(backup_path) as zf:
        settings = json.loads(zf.read("settings.json"))

    assert settings["emby.api_key"].startswith(ENCRYPTED_PREFIX)
    assert "super-secret" not in settings["emby.api_key"]
    assert settings["emby.url"] == "http://emby.local:8096"


def test_pg_dump_enabled_by_default():
    """pg_dump defaults to ON so scheduled backups capture the DB
    instead of shipping JSON metadata only."""
    assert DEFAULT_COMPONENTS["pg_dump"] is True


@pytest.mark.asyncio
async def test_create_backup_runs_pg_dump_with_default_components(
    db_session, patched_backup_dir, stub_pg_dump,
):
    """With ``components=None`` the default profile must trigger pg_dump and
    embed the SQL output in the archive."""
    pg_mock, fake_sql = stub_pg_dump

    backup_path = await create_backup(db_session)

    pg_mock.assert_awaited_once()
    with zipfile.ZipFile(backup_path) as zf:
        names = zf.namelist()
        assert "pg_dump.sql" in names
        assert zf.read("pg_dump.sql").decode("utf-8") == fake_sql
        manifest = json.loads(zf.read("manifest.json"))

    assert manifest["components"]["pg_dump"] is True


@pytest.mark.asyncio
async def test_create_backup_embeds_persistent_key_from_env(
    db_session, patched_backup_dir, stub_pg_dump, monkeypatch,
):
    env_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("MEDIAKEEPER_ENCRYPTION_KEY", env_key)

    backup_path = await create_backup(
        db_session,
        components={
            "settings": True,
            "preferences": False,
            "scheduler": False,
            "watchlist": False,
            "logs": False,
            "pg_dump": False,
        },
    )

    with zipfile.ZipFile(backup_path) as zf:
        assert ENCRYPTION_KEY_ARCHIVE_NAME in zf.namelist()
        embedded = zf.read(ENCRYPTION_KEY_ARCHIVE_NAME).decode("ascii")
        manifest = json.loads(zf.read("manifest.json"))

    assert embedded == env_key
    assert manifest["encryption_key"]["status"] == "included"
    assert manifest["encryption_key"]["source"] == "env"
    assert manifest["encryption_key"]["archive_path"] == ENCRYPTION_KEY_ARCHIVE_NAME
    assert manifest["encryption_key"]["warning"]


@pytest.mark.asyncio
async def test_create_backup_embeds_persistent_key_from_file(
    db_session, patched_backup_dir, stub_pg_dump, monkeypatch, tmp_path,
):
    file_key = Fernet.generate_key().decode("ascii")
    key_file = tmp_path / "encryption_key"
    key_file.write_text(file_key, encoding="ascii")

    monkeypatch.delenv("MEDIAKEEPER_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(
        "core.encryption._KEY_FILE_PATHS",
        (key_file,),
    )

    backup_path = await create_backup(
        db_session,
        components={
            "settings": True,
            "preferences": False,
            "scheduler": False,
            "watchlist": False,
            "logs": False,
            "pg_dump": False,
        },
    )

    with zipfile.ZipFile(backup_path) as zf:
        assert ENCRYPTION_KEY_ARCHIVE_NAME in zf.namelist()
        embedded = zf.read(ENCRYPTION_KEY_ARCHIVE_NAME).decode("ascii")
        manifest = json.loads(zf.read("manifest.json"))

    assert embedded == file_key
    assert manifest["encryption_key"]["status"] == "included"
    assert manifest["encryption_key"]["source"] == "file"


@pytest.mark.asyncio
async def test_create_backup_skips_key_when_only_ephemeral(
    db_session, patched_backup_dir, stub_pg_dump, monkeypatch, tmp_path, caplog,
):
    monkeypatch.delenv("MEDIAKEEPER_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(
        "core.encryption._KEY_FILE_PATHS",
        (tmp_path / "missing-key",),
    )

    with caplog.at_level("WARNING", logger="mediakeeper.backup"):
        backup_path = await create_backup(
            db_session,
            components={
                "settings": True,
                "preferences": False,
                "scheduler": False,
                "watchlist": False,
                "logs": False,
                "pg_dump": False,
            },
        )

    with zipfile.ZipFile(backup_path) as zf:
        names = zf.namelist()
        manifest = json.loads(zf.read("manifest.json"))

    assert ENCRYPTION_KEY_ARCHIVE_NAME not in names
    assert manifest["encryption_key"]["status"] == "absent"
    assert manifest["encryption_key"]["source"] is None
    assert manifest["encryption_key"]["archive_path"] is None
    assert manifest["encryption_key"]["warning"]
    assert any(
        "without secrets/.encryption_key" in record.message
        for record in caplog.records
    )
