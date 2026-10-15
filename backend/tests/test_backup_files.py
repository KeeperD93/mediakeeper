"""Backup file endpoints act only on existing backup archives: anything else
(missing backup, foreign file) is a 404 that leaves the directory untouched."""
import pytest

BACKUP = "mediakeeper_backup_20260101_120000.zip"


@pytest.fixture
def backup_dir(workspace_tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_PATH", str(workspace_tmp_path))
    return workspace_tmp_path


@pytest.mark.asyncio
async def test_delete_removes_the_backup(authed_client, backup_dir):
    (backup_dir / BACKUP).write_bytes(b"x")

    resp = await authed_client.delete(f"/api/backup/{BACKUP}")

    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    assert not (backup_dir / BACKUP).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("filename", [BACKUP, "notes.zip"])
async def test_delete_refuses_missing_or_foreign_files(authed_client, backup_dir, filename):
    (backup_dir / "notes.zip").write_bytes(b"x")

    resp = await authed_client.delete(f"/api/backup/{filename}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "backup_not_found"
    assert (backup_dir / "notes.zip").exists()
