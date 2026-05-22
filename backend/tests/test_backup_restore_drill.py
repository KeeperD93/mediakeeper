"""Smoke test — restore drill (opt-in only).

Skipped by default. Activate locally with ``MK_DRILL_ENABLED=1`` to run.

Validates the ``create_backup → ZIP → restore_backup`` round-trip on the
applicative KV layer (settings/preferences/scheduler/watchlist). The
``pg_dump`` branch is mocked because this smoke test does not spin up a
PostgreSQL container by design — that drill is documented manually in
``docs/operations/backup-restore.md``. The point of the smoke test is
to keep the application-side chain green in pytest without dragging
``testcontainers`` into CI.
"""
import json
import os
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from services.backup.create import create_backup
from services.backup.restore import restore_backup
from services.settings import get_setting, set_setting

pytestmark = pytest.mark.skipif(
    not os.getenv("MK_DRILL_ENABLED"),
    reason="Restore drill smoke test — opt-in via MK_DRILL_ENABLED=1",
)


@pytest.fixture
def drill_backup_dir(workspace_tmp_path, monkeypatch):
    monkeypatch.setattr(
        "services.backup.create.get_current_backup_dir",
        lambda: Path(workspace_tmp_path),
    )
    return workspace_tmp_path


@pytest.fixture
def drill_pg_dump_stub():
    fake_sql = "-- mocked pg_dump for smoke drill --\nSELECT 1;\n"
    with patch(
        "services.backup.create._pg_dump_async",
        new=AsyncMock(return_value=fake_sql),
    ) as mocked:
        yield mocked, fake_sql


@pytest.mark.asyncio
async def test_restore_round_trip_keeps_kv_layer(
    db_session, drill_backup_dir, drill_pg_dump_stub,
):
    await set_setting(db_session, "drill.smoke", "before")

    backup_path = await create_backup(db_session)

    with zipfile.ZipFile(backup_path) as zf:
        names = zf.namelist()
        assert "pg_dump.sql" in names, "regression: pg_dump.sql missing"
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["version"] == "1.1"

    await set_setting(db_session, "drill.smoke", "tampered")

    results = await restore_backup(
        db_session,
        backup_path,
        components={
            "settings": True,
            "preferences": True,
            "scheduler": True,
            "watchlist": True,
        },
    )

    assert results["settings"] == "ok"
    assert "encryption_key" in results
    assert await get_setting(db_session, "drill.smoke") == "before"
