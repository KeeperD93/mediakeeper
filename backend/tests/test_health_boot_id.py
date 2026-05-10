"""Tests for the boot_id field exposed by /api/health."""

import re

import pytest

from api import core_routes


@pytest.mark.asyncio
async def test_health_exposes_boot_id(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "boot_id" in data
    assert isinstance(data["boot_id"], str)
    assert data["boot_id"]


@pytest.mark.asyncio
async def test_health_boot_id_is_stable_across_calls(client):
    first = (await client.get("/api/health")).json()["boot_id"]
    second = (await client.get("/api/health")).json()["boot_id"]
    assert first == second
    assert first == core_routes.BOOT_ID


@pytest.mark.asyncio
async def test_health_boot_id_format_is_hex32(client):
    boot_id = (await client.get("/api/health")).json()["boot_id"]
    assert re.fullmatch(r"[0-9a-f]{32}", boot_id)
