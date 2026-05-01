import asyncio
from contextlib import suppress
from unittest.mock import AsyncMock, patch

import pytest

import api.healthcheck as healthcheck_api
from core.security import create_access_token
from services.scheduler import TASK_DEFINITIONS


def _csrf_headers(client):
    return {
        "x-csrf-token": client.cookies.get("mk_csrf", ""),
        "origin": "http://test",
    }


@pytest.mark.asyncio
async def test_me_bootstraps_csrf_cookie_for_admin_session(raw_client, admin_user):
    client = raw_client
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username}))

    resp = await client.get("/api/auth/me")

    assert resp.status_code == 200
    assert client.cookies.get("mk_csrf")
    set_cookie_headers = resp.headers.get_list("set-cookie")
    assert any("SameSite=lax" in header for header in set_cookie_headers)


@pytest.mark.asyncio
async def test_admin_enter_requires_valid_csrf_header(raw_client, admin_user):
    client = raw_client
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username}))
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
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username}))
    await client.get("/api/auth/me")

    resp = await client.post("/api/portal/admin/requests/enter", headers={
        "x-csrf-token": client.cookies.get("mk_csrf", ""),
        "origin": "http://evil.example",
    })

    assert resp.status_code == 403
    assert resp.json()["detail"] == "csrf_origin_mismatch"


@pytest.mark.asyncio
async def test_scheduler_run_returns_conflict_when_task_already_running(raw_client, admin_user):
    client = raw_client
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username}))
    await client.get("/api/auth/me")
    task_key = next(iter(TASK_DEFINITIONS.keys()))

    class FakeScheduler:
        def is_task_running(self, key):
            return True

    with patch("api.scheduler.get_scheduler", return_value=FakeScheduler()):
        resp = await client.post(f"/api/scheduler/tasks/{task_key}/run", headers=_csrf_headers(client))

    assert resp.status_code == 409
    assert resp.json()["detail"] == "task_already_running"


@pytest.mark.asyncio
async def test_healthcheck_and_watchlist_refuse_duplicate_manual_runs(raw_client, admin_user):
    client = raw_client
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username}))
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
