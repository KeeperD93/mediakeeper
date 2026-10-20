import json
import logging
import os
import time
import zipfile
from pathlib import Path
from typing import get_args
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from pydantic import ValidationError

from api.backup._schemas import BackupRequest, RestoreRequest
from api.backup._shared import _parse_components_payload
from constants.backup import BACKUP_LABEL_MAX_LENGTH
from core.encryption import ENCRYPTED_PREFIX
from services.backup import DEFAULT_COMPONENTS, ComponentName, get_backup_path
from services.backup import create as backup_create
from services.backup.create import (
    ENCRYPTION_KEY_ARCHIVE_NAME,
    create_backup,
)
from services.settings import set_setting

NO_COMPONENTS = dict.fromkeys(DEFAULT_COMPONENTS, False)


@pytest.fixture
def patched_backup_dir(workspace_tmp_path, monkeypatch):
    monkeypatch.setattr(
        "services.backup.create.resolve_backup_dir",
        AsyncMock(return_value=Path(workspace_tmp_path)),
    )
    return workspace_tmp_path


@pytest.fixture
def stub_pg_dump():
    """Replace the real pg_dump subprocess with a deterministic mock so the
    backup test suite never spawns Postgres binaries in CI."""
    fake_sql = "-- mocked pg_dump --\nSELECT 1;\n"
    with patch(
        "services.backup.create.dump_database",
        new=AsyncMock(return_value=fake_sql),
    ) as mocked:
        yield mocked, fake_sql


@pytest.mark.asyncio
async def test_create_backup_keeps_sensitive_settings_encrypted(
    db_session, patched_backup_dir, stub_pg_dump,
):
    await set_setting(db_session, "emby.api_key", "super-secret")
    await set_setting(db_session, "emby.url", "http://emby.local:8096")

    backup_path = (await create_backup(
        db_session,
        components={
            "settings": True,
            "preferences": False,
            "scheduler": False,
            "watchlist": False,
            "logs": False,
            "pg_dump": False,
        },
    )).path

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

    backup_path = (await create_backup(db_session)).path

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

    backup_path = (await create_backup(
        db_session,
        components={
            "settings": True,
            "preferences": False,
            "scheduler": False,
            "watchlist": False,
            "logs": False,
            "pg_dump": False,
        },
    )).path

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

    backup_path = (await create_backup(
        db_session,
        components={
            "settings": True,
            "preferences": False,
            "scheduler": False,
            "watchlist": False,
            "logs": False,
            "pg_dump": False,
        },
    )).path

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
        backup_path = (await create_backup(
            db_session,
            components={
                "settings": True,
                "preferences": False,
                "scheduler": False,
                "watchlist": False,
                "logs": False,
                "pg_dump": False,
            },
        )).path

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


@pytest.mark.asyncio
@pytest.mark.parametrize(("label", "suffix"), [("auto", "_auto"), ("Été 2026!", "_t2026"), ("!!!", "")])
async def test_label_keeps_only_what_the_file_routes_accept(
    db_session, patched_backup_dir, label, suffix,
):
    """An accented or symbol-only label used to name a backup that download,
    delete and restore then refused."""
    backup_path = (await create_backup(db_session, components=NO_COMPONENTS, label=label)).path

    assert backup_path.name.endswith(f"{suffix}.zip")
    assert get_backup_path(backup_path.name, patched_backup_dir) is not None


def test_label_is_capped_like_the_file_name():
    with pytest.raises(ValidationError):
        BackupRequest(label="x" * (BACKUP_LABEL_MAX_LENGTH + 1))


@pytest.mark.asyncio
async def test_a_label_at_the_cap_still_names_a_reachable_backup(db_session, patched_backup_dir):
    """The API cap, the archive writer and the file routes' name check agree."""
    label = "x" * BACKUP_LABEL_MAX_LENGTH
    BackupRequest(label=label)

    backup_path = (await create_backup(db_session, components=NO_COMPONENTS, label=label)).path

    assert backup_path.name.endswith(f"_{label}.zip")
    assert get_backup_path(backup_path.name, patched_backup_dir) is not None


@pytest.mark.asyncio
async def test_a_failed_part_is_left_out_and_reported(db_session, patched_backup_dir, monkeypatch):
    """A failed export used to leave a backup announced as complete, its
    manifest still listing the missing part."""
    monkeypatch.setattr("services.backup.create.dump_database", AsyncMock(return_value=None))
    monkeypatch.setattr(
        "services.backup.create.get_all_settings", AsyncMock(side_effect=RuntimeError("db gone")),
    )

    result = await create_backup(db_session)

    assert result.failed == ("settings", "pg_dump")
    with zipfile.ZipFile(result.path) as zf:
        names = zf.namelist()
        manifest = json.loads(zf.read("manifest.json"))
    assert "pg_dump.sql" not in names
    assert "settings.json" not in names
    assert "preferences.json" in names
    assert manifest["failed"] == ["settings", "pg_dump"]
    assert manifest["components"] == {
        "settings": False, "preferences": True, "scheduler": True,
        "watchlist": True, "logs": False, "pg_dump": False,
    }


@pytest.mark.asyncio
async def test_a_complete_backup_reports_no_missing_part(db_session, patched_backup_dir, stub_pg_dump):
    result = await create_backup(db_session)

    assert result.failed == ()
    with zipfile.ZipFile(result.path) as zf:
        manifest = json.loads(zf.read("manifest.json"))
    assert manifest["failed"] == []
    assert manifest["components"]["pg_dump"] is True


@pytest.mark.asyncio
async def test_the_archive_takes_its_name_only_once_complete(db_session, patched_backup_dir, monkeypatch):
    """Written under a temporary name, then moved in place: the listing never
    meets a half-written backup."""
    real_embed = backup_create._embed_encryption_key
    during_write = []

    def embed(zf):
        during_write.append(sorted(p.name for p in Path(patched_backup_dir).iterdir()))
        return real_embed(zf)

    monkeypatch.setattr(backup_create, "_embed_encryption_key", embed)

    backup_path = (await create_backup(db_session, components=NO_COMPONENTS)).path

    [[tmp_name]] = during_write
    assert tmp_name.startswith(backup_path.name + ".") and tmp_name.endswith(".part")
    assert sorted(p.name for p in Path(patched_backup_dir).iterdir()) == [backup_path.name]


def test_two_writes_of_one_archive_use_their_own_temporary_file(tmp_path, monkeypatch):
    """Two backups started in the same second share their final name: each one
    writes its own temporary file, so neither can corrupt the other."""
    monkeypatch.setattr(backup_create, "_embed_encryption_key", lambda zf: {"status": "absent"})
    real_zipfile = backup_create.zipfile.ZipFile
    written = []

    def zipfile_spy(path, *args, **kwargs):
        written.append(Path(path).name)
        return real_zipfile(path, *args, **kwargs)

    monkeypatch.setattr(backup_create.zipfile, "ZipFile", zipfile_spy)
    dest = tmp_path / "mediakeeper_backup_20260101_000000.zip"

    backup_create._write_archive(dest, [], {}, "", [])
    backup_create._write_archive(dest, [], {}, "", [])

    assert len(written) == 2 and written[0] != written[1]
    assert sorted(p.name for p in tmp_path.iterdir()) == [dest.name]


@pytest.mark.asyncio
async def test_a_write_cut_short_leaves_no_archive_behind(db_session, patched_backup_dir, monkeypatch):
    """A failure while writing (full disk) leaves neither a truncated backup
    nor the temporary file."""
    monkeypatch.setattr(
        backup_create, "_embed_encryption_key", MagicMock(side_effect=OSError("disk full")),
    )

    with pytest.raises(OSError, match="disk full"):
        await create_backup(db_session, components=NO_COMPONENTS)

    assert list(Path(patched_backup_dir).iterdir()) == []


def _age_past_cutoff(*files):
    """Date files back to just over a day: what a crash left behind long ago."""
    then = time.time() - backup_create.STALE_TEMP_AGE_S - 60
    for f in files:
        os.utime(f, (then, then))


def test_old_temporary_archives_are_removed(tmp_path):
    """A write cut short (crash, restart) leaves its temporary file: once a day
    old it goes. A younger one may belong to a backup still running, and a file
    that is not a backup's own is none of our business: both stay."""
    old = tmp_path / "mediakeeper_backup_20260101_000000.zip.0a1b2c.part"
    young = tmp_path / "mediakeeper_backup_20260102_000000.zip.3d4e5f.part"
    other = tmp_path / "notes.part"
    for f in (old, young, other):
        f.write_bytes(b"x")
    _age_past_cutoff(old, other)

    backup_create._remove_stale_temp_archives(tmp_path)

    assert sorted(p.name for p in tmp_path.iterdir()) == [young.name, other.name]


@pytest.mark.asyncio
async def test_a_backup_clears_old_temporary_archives_first(db_session, patched_backup_dir):
    leftover = Path(patched_backup_dir) / "mediakeeper_backup_20260101_000000.zip.0a1b2c.part"
    leftover.write_bytes(b"x")
    _age_past_cutoff(leftover)

    backup_path = (await create_backup(db_session, components=NO_COMPONENTS)).path

    assert sorted(p.name for p in Path(patched_backup_dir).iterdir()) == [backup_path.name]


def test_a_temporary_archive_that_will_not_go_never_stops_a_backup(tmp_path, monkeypatch, caplog):
    leftover = tmp_path / "mediakeeper_backup_20260101_000000.zip.0a1b2c.part"
    leftover.write_bytes(b"x")
    _age_past_cutoff(leftover)
    monkeypatch.setattr(Path, "unlink", MagicMock(side_effect=PermissionError("locked")))

    with caplog.at_level(logging.WARNING, logger="mediakeeper.backup"):
        backup_create._remove_stale_temp_archives(tmp_path)

    assert leftover.exists()
    assert "Could not remove" in caplog.text


def test_component_names_match_the_backup_parts():
    assert set(get_args(ComponentName)) == set(DEFAULT_COMPONENTS)


@pytest.mark.parametrize("components", [{"settings": "false"}, {"settings": 1}, {"secrets": True}])
def test_a_component_selection_takes_known_parts_and_booleans_only(components):
    """``{"settings": "false"}`` used to export the settings anyway."""
    with pytest.raises(ValidationError):
        BackupRequest(components=components)
    with pytest.raises(ValidationError):
        RestoreRequest(filename="mediakeeper_backup_x.zip", components=components)
    with pytest.raises(HTTPException) as refused:
        _parse_components_payload(json.dumps(components))
    assert refused.value.detail == "backup_components_invalid"
