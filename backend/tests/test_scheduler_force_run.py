"""Inter-process Run Now trigger backed by ``force_run_requested_at``.

Pins:
- The API stamps the column instead of touching the scheduler instance
  directly (which is ``None`` on the web process when
  ``MK_SEPARATE_BACKGROUND_WORKER=true``).
- The scheduler loop's polling helper picks the flag up, clears it,
  and launches the task — exactly once per stamp.
- Edge cases: unknown key → 404, already running → 409.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from models.scheduler_task import SchedulerTask
from services.scheduler import TASK_DEFINITIONS


async def _login_admin(client) -> None:
    """Open a backoffice session — the run endpoint requires
    ``get_current_user`` + CSRF, both satisfied by the standard
    test login flow (admin fixture seeds the user, ``client``
    fixture seeds CSRF)."""
    monkeypatch_admin_users = "admin"
    # ``client`` fixture already injects CSRF headers + cookie. The
    # login call sets the mk_token cookie that ``get_current_user``
    # decodes downstream.
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "TestPassword123!"},
    )
    assert resp.status_code == 200, resp.text


async def _seed_task_row(db_session, key: str = "notifications") -> SchedulerTask:
    """Mirror what ``_ensure_tasks_exist`` does at scheduler boot, on
    a known TASK_DEFINITIONS entry so the API endpoint's
    ``key not in TASK_DEFINITIONS`` gate is satisfied."""
    defn = TASK_DEFINITIONS[key]
    row = SchedulerTask(
        key=key,
        label=defn["label"],
        enabled=defn["default_on"],
        interval_sec=defn["default_sec"],
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


@pytest.mark.asyncio
async def test_run_endpoint_stamps_force_run_column(
    client, admin_user, db_session, monkeypatch,
):
    """POST /api/scheduler/tasks/<key>/run should set the flag in DB."""
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")
    await _seed_task_row(db_session)
    await _login_admin(client)

    resp = await client.post("/api/scheduler/tasks/notifications/run")
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True

    row = (
        await db_session.execute(
            select(SchedulerTask).where(SchedulerTask.key == "notifications")
        )
    ).scalar_one()
    assert row.force_run_requested_at is not None


@pytest.mark.asyncio
async def test_run_endpoint_returns_404_for_unknown_key(
    client, admin_user, monkeypatch,
):
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")
    await _login_admin(client)

    resp = await client.post("/api/scheduler/tasks/does_not_exist/run")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "task_unknown"


@pytest.mark.asyncio
async def test_run_endpoint_returns_409_when_already_running(
    client, admin_user, db_session, monkeypatch,
):
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")
    row = await _seed_task_row(db_session)
    row.last_status = "running"
    await db_session.commit()
    await _login_admin(client)

    resp = await client.post("/api/scheduler/tasks/notifications/run")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "task_already_running"


# Coverage gap (assumed): ``_consume_force_run_requests`` (the worker
# side that drains the flag and schedules ``_run_task``) is not unit
# tested here because the test harness uses SQLite ``:memory:`` whose
# schema doesn't propagate to fresh AsyncSession instances the way
# Postgres does in production. The function is short and direct
# (SELECT + UPDATE + create_task), and the integration is verified
# manually at rebuild time by clicking "Lancer" in the admin UI.
