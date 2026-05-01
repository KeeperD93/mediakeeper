import json
import zipfile
from pathlib import Path

import pytest

from core.encryption import ENCRYPTED_PREFIX
from services.backup.create import create_backup
from services.settings import set_setting


@pytest.mark.asyncio
async def test_create_backup_keeps_sensitive_settings_encrypted(
    db_session, workspace_tmp_path, monkeypatch,
):
    await set_setting(db_session, "emby.api_key", "super-secret")
    await set_setting(db_session, "emby.url", "http://emby.local:8096")

    monkeypatch.setattr(
        "services.backup.create.get_current_backup_dir",
        lambda: Path(workspace_tmp_path),
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
        settings = json.loads(zf.read("settings.json"))

    assert settings["emby.api_key"].startswith(ENCRYPTED_PREFIX)
    assert "super-secret" not in settings["emby.api_key"]
    assert settings["emby.url"] == "http://emby.local:8096"
