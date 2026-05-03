"""Jellystats import endpoint coverage."""
from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch

import pytest

from core.security import create_access_token


@pytest.mark.asyncio
async def test_jellystats_import_rejects_non_json(client, admin_user):
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    resp = await client.post(
        "/api/stats/import/jellystats",
        files={"file": ("backup.txt", io.BytesIO(b"{}"), "text/plain")},
    )

    assert resp.status_code == 200
    assert resp.json()["error"] == "File must be in JSON format"


@pytest.mark.asyncio
async def test_jellystats_import_reads_valid_json(client, admin_user):
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    with patch(
        "api.stats._import.import_jellystats_backup",
        new=AsyncMock(return_value={"imported": 1}),
    ):
        resp = await client.post(
            "/api/stats/import/jellystats",
            files={"file": ("backup.JSON", io.BytesIO(b'{"items": []}'), "application/json")},
        )

    assert resp.status_code == 200
    assert resp.json() == {"imported": 1}


@pytest.mark.asyncio
async def test_jellystats_import_stops_when_file_is_too_large(client, admin_user, monkeypatch):
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))
    monkeypatch.setattr("api.stats._import._MAX_IMPORT_SIZE", 8)

    resp = await client.post(
        "/api/stats/import/jellystats",
        files={"file": ("backup.json", io.BytesIO(b'{"items": []}'), "application/json")},
    )

    assert resp.status_code == 200
    assert "File too large" in resp.json()["error"]
