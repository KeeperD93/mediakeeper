import asyncio
from contextlib import suppress
from unittest.mock import AsyncMock, patch

import pytest

import api.healthcheck as healthcheck_api
from core.security import create_access_token


def _csrf_headers(client):
    return {
        "x-csrf-token": client.cookies.get("mk_csrf", ""),
        "origin": "http://test",
    }


@pytest.mark.asyncio
async def test_me_bootstraps_csrf_cookie_for_admin_session(raw_client, admin_user):
    client = raw_client
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    resp = await client.get("/api/auth/me")

    assert resp.status_code == 200
    assert client.cookies.get("mk_csrf")
    set_cookie_headers = resp.headers.get_list("set-cookie")
    assert any("SameSite=lax" in header for header in set_cookie_headers)


@pytest.mark.asyncio
async def test_admin_enter_requires_valid_csrf_header(raw_client, admin_user):
    client = raw_client
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))
    await client.get("/api/auth/me")

    blocked = await client.post("/api/portal/admin/requests/enter")
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "csrf_token_invalid"

    allowed = await client.post("/api/portal/admin/requests/enter", headers=_csrf_headers(client))
    assert allowed.status_code == 200
    assert client.cookies.get("rq_token")


@pytest.mark.asyncio
async def test_admin_enter_rejects_cross_origin_even_with_valid_token(raw_client, admin_user):
    client = raw_client
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))
    await client.get("/api/auth/me")

    resp = await client.post("/api/portal/admin/requests/enter", headers={
        "x-csrf-token": client.cookies.get("mk_csrf", ""),
        "origin": "http://evil.example",
    })

    assert resp.status_code == 403
    assert resp.json()["detail"] == "csrf_origin_mismatch"


# Note: the equivalent 409 / 404 / stamping tests for the scheduler
# "Run Now" endpoint have moved to ``test_scheduler_force_run.py``
# since the API no longer dispatches through ``get_scheduler()`` —
# it stamps the ``force_run_requested_at`` column instead so the
# worker process picks the trigger up via DB polling.


@pytest.mark.asyncio
async def test_healthcheck_and_watchlist_refuse_duplicate_manual_runs(raw_client, admin_user):
    client = raw_client
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))
    await client.get("/api/auth/me")

    sleep_task = asyncio.create_task(asyncio.sleep(60))
    previous_task = healthcheck_api._scan_task
    healthcheck_api._scan_task = sleep_task
    try:
        health_resp = await client.post("/api/healthcheck/scan", headers=_csrf_headers(client))
    finally:
        healthcheck_api._scan_task = previous_task
        sleep_task.cancel()
        with suppress(asyncio.CancelledError):
            await sleep_task

    assert health_resp.status_code == 409
    assert health_resp.json()["detail"] == "scan_already_running"

    with patch("api.watchlist.incremental_scan", new=AsyncMock(return_value={"error": "scan_already_running"})):
        watchlist_resp = await client.post("/api/watchlist/scan/refresh", headers=_csrf_headers(client))

    assert watchlist_resp.status_code == 409
    assert watchlist_resp.json()["detail"] == "scan_already_running"
