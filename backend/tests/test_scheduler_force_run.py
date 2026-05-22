"""Inter-process Run Now trigger backed by ``force_run_requested_at``.

Pins:
- The API stamps the column instead of touching the scheduler instance
  directly (which is ``None`` on the web process when
  ``MK_SEPARATE_BACKGROUND_WORKER=true``).
- The scheduler loop's polling helper picks the flag up, clears it,
  and launches the task — exactly once per stamp.
- Edge cases: unknown key → 404, already running → 409.

Both sides of the bridge are covered: the API stamp path (via the
HTTP fixtures) and the worker drain path (via a dedicated engine with
``StaticPool`` so the seeded row is visible from the fresh sessions the
``Scheduler`` instance spins up).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from models.base import Base
from models.scheduler_task import SchedulerTask, TaskStatus
from services.scheduler import TASK_DEFINITIONS
from services.scheduler._scheduler import Scheduler


async def _login_admin(client) -> None:
    """Open a backoffice session — the run endpoint requires
    ``get_current_user`` + CSRF, both satisfied by the standard
    test login flow (admin fixture seeds the user, ``client``
    fixture seeds CSRF)."""
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
    row.last_status = TaskStatus.RUNNING.value
    await db_session.commit()
    await _login_admin(client)

    resp = await client.post("/api/scheduler/tasks/notifications/run")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "task_already_running"


# ─── Worker side: ``_consume_force_run_requests`` ────────────────────
#
# A dedicated engine with ``StaticPool`` lets the function spin up
# its own ``AsyncSession`` and still see the seeded row — the
# default test harness uses a connection-per-session pool which
# fragments the ``:memory:`` DB.


@pytest_asyncio.fixture
async def shared_engine():
    """Engine where every connection sees the same in-memory DB."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _seed_force_run(
    engine,
    key: str = "notifications",
    *,
    last_status: str | None = None,
) -> None:
    """Insert a task row with the force-run flag set, optionally
    marking it as already running for the skip-test below."""
    defn = TASK_DEFINITIONS[key]
    async with AsyncSession(engine, expire_on_commit=False) as db:
        row = SchedulerTask(
            key=key,
            label=defn["label"],
            enabled=defn["default_on"],
            interval_sec=defn["default_sec"],
            force_run_requested_at=datetime.now(timezone.utc),
            last_status=last_status,
        )
        db.add(row)
        await db.commit()


@pytest.mark.asyncio
async def test_consume_force_run_drains_and_dispatches(shared_engine, monkeypatch):
    """Happy path: flag is set, ``_run_task`` is launched for the key,
    and the column is cleared in the same pass."""
    await _seed_force_run(shared_engine, key="notifications")

    scheduler = Scheduler(shared_engine)
    launched: list[str] = []

    async def fake_run_task(key):
        launched.append(key)

    monkeypatch.setattr(scheduler, "_run_task", fake_run_task)

    await scheduler._consume_force_run_requests()
    # ``asyncio.create_task`` schedules — yield once so the coroutine runs.
    await asyncio.sleep(0)

    async with AsyncSession(shared_engine, expire_on_commit=False) as db:
        row = (
            await db.execute(
                select(SchedulerTask).where(SchedulerTask.key == "notifications")
            )
        ).scalar_one()
        assert row.force_run_requested_at is None, "flag must be cleared"

    assert launched == ["notifications"]


@pytest.mark.asyncio
async def test_consume_force_run_skips_already_running_task(shared_engine, monkeypatch):
    """If the task is in the ``_running_tasks`` set, skip the dispatch
    but still clear the flag — otherwise the next tick would re-trigger
    forever once the in-progress run finishes."""
    await _seed_force_run(shared_engine, key="notifications")

    scheduler = Scheduler(shared_engine)
    scheduler._running_tasks.add("notifications")
    launched: list[str] = []

    async def fake_run_task(key):
        launched.append(key)

    monkeypatch.setattr(scheduler, "_run_task", fake_run_task)

    await scheduler._consume_force_run_requests()
    await asyncio.sleep(0)

    async with AsyncSession(shared_engine, expire_on_commit=False) as db:
        row = (
            await db.execute(
                select(SchedulerTask).where(SchedulerTask.key == "notifications")
            )
        ).scalar_one()
        assert row.force_run_requested_at is None

    assert launched == []


@pytest.mark.asyncio
async def test_consume_force_run_skips_unknown_task_key(shared_engine, monkeypatch):
    """Orphan row whose key was removed from ``TASK_DEFINITIONS``:
    clear the flag (so we don't loop) but don't try to dispatch a
    handler that no longer exists."""
    defn = TASK_DEFINITIONS["notifications"]
    async with AsyncSession(shared_engine, expire_on_commit=False) as db:
        row = SchedulerTask(
            key="ghost_task",
            label=defn["label"],
            enabled=False,
            interval_sec=defn["default_sec"],
            force_run_requested_at=datetime.now(timezone.utc),
        )
        db.add(row)
        await db.commit()

    scheduler = Scheduler(shared_engine)
    launched: list[str] = []

    async def fake_run_task(key):
        launched.append(key)

    monkeypatch.setattr(scheduler, "_run_task", fake_run_task)

    await scheduler._consume_force_run_requests()
    await asyncio.sleep(0)

    async with AsyncSession(shared_engine, expire_on_commit=False) as db:
        row = (
            await db.execute(
                select(SchedulerTask).where(SchedulerTask.key == "ghost_task")
            )
        ).scalar_one()
        assert row.force_run_requested_at is None

    assert launched == []
