"""Tests that the scheduler dispatches a monitoring alert when a task raises."""
from unittest.mock import AsyncMock, patch

import pytest

from services.monitoring import AlertType, reset_debounce_state
from services.scheduler._scheduler import Scheduler


@pytest.fixture(autouse=True)
def _reset_state():
    reset_debounce_state()
    yield
    reset_debounce_state()


@pytest.mark.asyncio
async def test_scheduler_alerts_when_task_handler_raises(monkeypatch):
    """A handler exception must trigger a SCHEDULER_TASK_CRASHED alert."""

    async def _broken_handler(_db):
        raise RuntimeError("simulated handler failure")

    fake_definition = {"label": "fake", "default_sec": 60, "default_on": True, "handler": _broken_handler}

    with patch.dict(
        "services.scheduler._scheduler.TASK_DEFINITIONS",
        {"fake_task": fake_definition},
        clear=False,
    ), patch("services.scheduler._scheduler._mark_running", new=AsyncMock()), patch(
        "services.scheduler._scheduler._mark_done", new=AsyncMock()
    ), patch("services.scheduler._scheduler.AsyncSession") as session_cls, patch(
        "services.monitoring.send_alert", new=AsyncMock(return_value=True)
    ) as alert_mock:
        # Make the AsyncSession context manager a no-op around our broken handler.
        session_cls.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        scheduler = Scheduler(engine=AsyncMock())
        await scheduler._exec_task("fake_task", fake_definition)

    alert_mock.assert_awaited_once()
    args, kwargs = alert_mock.await_args
    assert args[0] is AlertType.SCHEDULER_TASK_CRASHED
    assert args[1]["task"] == "fake_task"
    assert "simulated handler failure" in args[1]["error"]
