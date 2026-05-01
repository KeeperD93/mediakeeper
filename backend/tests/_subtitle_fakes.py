"""Fakes and shared helpers for subtitle tests."""
import uuid
from pathlib import Path


def _make_workspace_tmp() -> Path:
    root = Path(__file__).resolve().parent / "_tmp_subtitle_paths" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeProc:
    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode

    async def communicate(self):
        return self._stdout, self._stderr
