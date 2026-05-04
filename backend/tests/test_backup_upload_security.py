"""Integration tests covering the upload-restore archive validators."""
import io
import zipfile
from unittest.mock import AsyncMock, patch

import pytest

from core.security import create_access_token


def _build_zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries:
            zf.writestr(name, payload)
    buf.seek(0)
    return buf


def _build_legitimate_backup_zip():
    return _build_zip(
        [
            ("manifest.json", b'{"version":"1.1","components":{}}'),
            ("settings.json", b"{}"),
        ]
    )


def _auth_admin(client, admin_user):
    client.cookies.set(
        "mk_token",
        create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )


@pytest.mark.asyncio
async def test_upload_restore_rejects_non_zip_magic_bytes(client, admin_user):
    """A file whose extension is .zip but whose body is not a ZIP archive
    must be refused before the restore pipeline is invoked."""
    _auth_admin(client, admin_user)
    payload = b"this is plain text pretending to be a zip"
    resp = await client.post(
        "/api/backup/upload-restore",
        files={"file": ("backup.zip", payload, "application/zip")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_archive_format"


@pytest.mark.asyncio
async def test_upload_restore_rejects_unknown_archive_entry(client, admin_user):
    """An archive that contains an entry outside the backup whitelist must
    be refused — no restore must happen."""
    _auth_admin(client, admin_user)
    buf = _build_zip(
        [
            ("manifest.json", b'{"version":"1.1"}'),
            ("malicious.bin", b"\x00\x01"),
        ]
    )
    with patch(
        "api.backup._restore.restore_backup", new=AsyncMock()
    ) as mock_restore:
        resp = await client.post(
            "/api/backup/upload-restore",
            files={"file": ("backup.zip", buf.getvalue(), "application/zip")},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "unknown_archive_entry"
    mock_restore.assert_not_called()


@pytest.mark.asyncio
async def test_upload_restore_rejects_path_traversal_namelist(
    client, admin_user
):
    """Traversal entries must trigger ``unsafe_archive_path`` regardless of
    whether the rest of the namelist is valid."""
    _auth_admin(client, admin_user)
    buf = _build_zip(
        [
            ("manifest.json", b'{"version":"1.1"}'),
            ("../escape.txt", b"x"),
        ]
    )
    with patch(
        "api.backup._restore.restore_backup", new=AsyncMock()
    ) as mock_restore:
        resp = await client.post(
            "/api/backup/upload-restore",
            files={"file": ("backup.zip", buf.getvalue(), "application/zip")},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "unsafe_archive_path"
    mock_restore.assert_not_called()


@pytest.mark.asyncio
async def test_upload_restore_rejects_empty_archive(client, admin_user):
    """A ZIP container with no entries cannot be a backup — refuse early."""
    _auth_admin(client, admin_user)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as _:
        pass
    buf.seek(0)
    resp = await client.post(
        "/api/backup/upload-restore",
        files={"file": ("backup.zip", buf.getvalue(), "application/zip")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "archive_empty"


@pytest.mark.asyncio
async def test_upload_restore_rejects_extreme_compression_ratio(
    client, admin_user
):
    """Per-entry uncompressed/compressed ratio above the configured cap is
    a zip-bomb signal — refused before any payload is read."""
    _auth_admin(client, admin_user)
    big_payload = b"A" * (256 * 1024)  # ~256 KiB of 'A' compresses to a few hundred bytes.
    buf = _build_zip([("settings.json", big_payload)])
    with patch(
        "api.backup._restore.restore_backup", new=AsyncMock()
    ) as mock_restore:
        resp = await client.post(
            "/api/backup/upload-restore",
            files={"file": ("backup.zip", buf.getvalue(), "application/zip")},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "archive_compression_ratio_suspicious"
    mock_restore.assert_not_called()


@pytest.mark.asyncio
async def test_upload_restore_accepts_legitimate_backup(client, admin_user):
    """A whitelisted, well-formed archive must reach the restore pipeline."""
    _auth_admin(client, admin_user)
    buf = _build_legitimate_backup_zip()
    with patch(
        "api.backup._restore.restore_backup",
        new=AsyncMock(return_value={"settings": "ok"}),
    ) as mock_restore:
        resp = await client.post(
            "/api/backup/upload-restore",
            files={"file": ("backup.zip", buf.getvalue(), "application/zip")},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["results"] == {"settings": "ok"}
    mock_restore.assert_called_once()


@pytest.mark.asyncio
async def test_upload_restore_still_rejects_wrong_extension(
    client, admin_user
):
    """Existing extension guard must keep rejecting non-.zip filenames so
    the new validators do not accidentally widen the surface."""
    _auth_admin(client, admin_user)
    resp = await client.post(
        "/api/backup/upload-restore",
        files={"file": ("backup.tar", b"unused", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "file_must_be_zip"
