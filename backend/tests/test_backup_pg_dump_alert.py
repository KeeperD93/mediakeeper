"""pg_dump failures must surface a runtime monitoring alert."""
from unittest.mock import AsyncMock, patch

import pytest

from services.backup.create import _pg_dump_async
from services.monitoring import AlertType, reset_debounce_state


@pytest.fixture(autouse=True)
def _reset_state():
    reset_debounce_state()
    yield
    reset_debounce_state()


class _FakeProc:
    def __init__(self, returncode: int, stderr: bytes = b"boom"):
        self.returncode = returncode
        self._stderr = stderr

    async def communicate(self):
        return b"", self._stderr


@pytest.mark.asyncio
async def test_pg_dump_failure_triggers_backup_alert(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://user:pwd@127.0.0.1:5432/mediakeeper_db",
    )

    async def _fake_create_subprocess(*_args, **_kwargs):
        return _FakeProc(returncode=2, stderr=b"permission denied")

    with patch("asyncio.create_subprocess_exec", new=_fake_create_subprocess), patch(
        "services.monitoring.send_alert", new=AsyncMock(return_value=True)
    ) as alert_mock:
        result = await _pg_dump_async()

    assert result is None
    alert_mock.assert_awaited_once()
    args, _ = alert_mock.await_args
    assert args[0] is AlertType.BACKUP_FAILED
    assert args[1]["component"] == "pg_dump"
    assert args[1]["returncode"] == 2
