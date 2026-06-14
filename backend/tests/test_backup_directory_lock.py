"""The backup directory lock (BACKUP_PATH) is surfaced explicitly.

When BACKUP_PATH pins the directory, /info must report it and set-directory
must return a dedicated, actionable code instead of a generic 400 — so the UI
can explain the lock rather than implying the submitted path is malformed.
"""
import pytest

from core.security import create_access_token


def _auth_admin(client, admin_user):
    client.cookies.set(
        "mk_token",
        create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )


@pytest.mark.asyncio
async def test_info_reports_locked_when_backup_path_set(client, admin_user, monkeypatch, tmp_path):
    _auth_admin(client, admin_user)
    monkeypatch.setenv("BACKUP_PATH", str(tmp_path / "bk"))

    resp = await client.get("/api/backup/info")

    assert resp.status_code == 200
    assert resp.json()["backup_dir_locked"] is True


@pytest.mark.asyncio
async def test_set_directory_returns_locked_code_when_backup_path_set(
    client, admin_user, monkeypatch, tmp_path
):
    _auth_admin(client, admin_user)
    monkeypatch.setenv("BACKUP_PATH", str(tmp_path / "bk"))

    resp = await client.post(
        "/api/backup/set-directory", json={"path": str(tmp_path / "other")}
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "backup_directory_locked"
