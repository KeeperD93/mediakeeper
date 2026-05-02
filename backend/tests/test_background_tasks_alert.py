"""BackgroundTaskManager._supervised must alert when a loop crashes."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from services.background_tasks import BackgroundTaskManager
from services.monitoring import AlertType, reset_debounce_state


@pytest.fixture(autouse=True)
def _reset_state():
    reset_debounce_state()
    yield
    reset_debounce_state()


@pytest.mark.asyncio
async def test_supervised_alerts_when_loop_crashes():
    manager = BackgroundTaskManager(engine=AsyncMock())

    async def _raises_then_cancels():
        raise RuntimeError("loop boom")

    sleep_calls = {"n": 0}

    async def _fake_sleep(_seconds):
        sleep_calls["n"] += 1
        # Break out of the supervisor's infinite retry on the second sleep.
        if sleep_calls["n"] >= 1:
            raise asyncio.CancelledError()

    with patch("services.background_tasks.asyncio.sleep", new=_fake_sleep), patch(
        "services.monitoring.send_alert", new=AsyncMock(return_value=True)
    ) as alert_mock:
        with pytest.raises(asyncio.CancelledError):
            await manager._supervised("test_loop", _raises_then_cancels, restart_delay=0.0)

    alert_mock.assert_awaited_once()
    args, _ = alert_mock.await_args
    assert args[0] is AlertType.BACKGROUND_LOOP_CRASHED
    assert args[1]["loop"] == "test_loop"
    assert "loop boom" in args[1]["error"]
