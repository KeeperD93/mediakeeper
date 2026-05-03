"""GET /api/health/encryption surfaces the Fernet key provenance.

The admin UI calls this once after login to decide whether to render
the persistent ephemeral-key banner. The endpoint is auth-gated so an
unauthenticated visitor cannot probe whether the deployment is using a
disposable in-memory key.
"""
from __future__ import annotations

from pathlib import Path

import pytest


async def _login(client) -> None:
    r = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_endpoint_requires_authentication(raw_client, monkeypatch):
    monkeypatch.setenv("MEDIAKEEPER_ENCRYPTION_KEY", "envkey")
    r = await raw_client.get("/api/health/encryption")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_reports_env_source_when_env_var_set(client, admin_user, monkeypatch):
    monkeypatch.setenv("MEDIAKEEPER_ENCRYPTION_KEY", "envkey")
    await _login(client)

    r = await client.get("/api/health/encryption")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"persistent": True, "source": "env", "warning": False}


@pytest.mark.asyncio
async def test_reports_file_source_when_key_file_present(
    client, admin_user, monkeypatch, workspace_tmp_path,
):
    monkeypatch.delenv("MEDIAKEEPER_ENCRYPTION_KEY", raising=False)
    key_file: Path = workspace_tmp_path / "encryption.key"
    key_file.write_text("filekey", encoding="ascii")
    monkeypatch.setenv("MEDIAKEEPER_ENCRYPTION_KEY_FILE", str(key_file))
    # The constants module captured ``_KEY_FILE_PATHS`` at import time, so we
    # rebuild the tuple to pick up the new env var.
    import core.encryption as enc
    monkeypatch.setattr(enc, "_KEY_FILE_PATHS", (key_file,))

    await _login(client)

    r = await client.get("/api/health/encryption")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"persistent": True, "source": "file", "warning": False}


@pytest.mark.asyncio
async def test_reports_ephemeral_when_no_persistent_source(
    client, admin_user, monkeypatch,
):
    monkeypatch.delenv("MEDIAKEEPER_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("MEDIAKEEPER_ENCRYPTION_KEY_FILE", raising=False)
    import core.encryption as enc
    monkeypatch.setattr(enc, "_KEY_FILE_PATHS", ())

    await _login(client)

    r = await client.get("/api/health/encryption")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"persistent": False, "source": "ephemeral", "warning": True}
