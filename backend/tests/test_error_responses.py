"""Server-side failures answer with codes, never English sentences: the
screens translate a ``detail`` code, or name the action that failed."""
from __future__ import annotations

import pytest
from starlette.requests import Request

import main
from core import app_startup


@pytest.mark.asyncio
async def test_requests_during_startup_get_the_starting_code(authed_client, monkeypatch):
    monkeypatch.setattr(app_startup, "_db_ready", False)

    resp = await authed_client.get("/api/backup/info")

    assert resp.status_code == 503
    assert resp.json() == {"detail": "starting"}


@pytest.mark.asyncio
async def test_an_unhandled_error_gives_no_detail_and_no_internals():
    request = Request({"type": "http", "method": "GET", "path": "/api/x", "headers": [], "query_string": b""})

    resp = await main.global_exception_handler(request, RuntimeError("db password=secret"))

    assert resp.status_code == 500
    assert resp.body == b'{"error":"internal_error"}'
