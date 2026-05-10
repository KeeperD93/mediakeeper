"""Boot-time cleanup of ``scheduler_tasks`` rows whose key is no longer
declared in ``TASK_DEFINITIONS``. Without this, a renamed/removed task
keeps showing up in the admin UI and any ``POST /run`` returns 404
because the runtime handler is gone."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from models.scheduler_task import SchedulerTask
from services.scheduler._db import _ensure_tasks_exist
from services.scheduler._tasks import TASK_DEFINITIONS


def _valid_key() -> str:
    return next(iter(TASK_DEFINITIONS))


async def _rows_by_key(db) -> dict[str, SchedulerTask]:
    rows = (await db.execute(select(SchedulerTask))).scalars().all()
    return {r.key: r for r in rows}


@pytest.mark.asyncio
async def test_orphan_row_is_deleted(db_session):
    db_session.add(SchedulerTask(
        key="doublons_scan",
        label="legacy",
        enabled=False,
        interval_sec=86400,
    ))
    await db_session.commit()

    await _ensure_tasks_exist(db_session)

    keys = await _rows_by_key(db_session)
    assert "doublons_scan" not in keys


@pytest.mark.asyncio
async def test_valid_row_is_preserved(db_session):
    key = _valid_key()
    db_session.add(SchedulerTask(
        key=key,
        label="preserved",
        enabled=True,
        interval_sec=12345,
    ))
    await db_session.commit()

    await _ensure_tasks_exist(db_session)

    rows = await _rows_by_key(db_session)
    assert key in rows
    assert rows[key].label == "preserved"
    assert rows[key].interval_sec == 12345


@pytest.mark.asyncio
async def test_idempotent(db_session):
    db_session.add(SchedulerTask(
        key="doublons_scan",
        label="legacy",
        enabled=False,
        interval_sec=86400,
    ))
    await db_session.commit()

    await _ensure_tasks_exist(db_session)
    first_keys = set((await _rows_by_key(db_session)).keys())

    await _ensure_tasks_exist(db_session)
    second_keys = set((await _rows_by_key(db_session)).keys())

    assert first_keys == second_keys
    assert "doublons_scan" not in second_keys
    assert first_keys == set(TASK_DEFINITIONS.keys())


@pytest.mark.asyncio
async def test_mixed_state(db_session):
    valid_keys = list(TASK_DEFINITIONS.keys())
    assert len(valid_keys) >= 2
    kept_key = valid_keys[0]
    missing_key = valid_keys[1]

    db_session.add(SchedulerTask(
        key=kept_key,
        label="kept",
        enabled=True,
        interval_sec=999,
    ))
    db_session.add(SchedulerTask(
        key="doublons_scan",
        label="legacy",
        enabled=False,
        interval_sec=86400,
    ))
    await db_session.commit()

    await _ensure_tasks_exist(db_session)

    rows = await _rows_by_key(db_session)
    assert "doublons_scan" not in rows
    assert kept_key in rows
    assert rows[kept_key].interval_sec == 999
    assert missing_key in rows
    assert rows[missing_key].interval_sec == TASK_DEFINITIONS[missing_key]["default_sec"]
