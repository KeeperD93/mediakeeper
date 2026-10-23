"""Every launch path caps WebSocket messages at what one chat frame needs: a
small compressed frame must never inflate to megabytes on the server."""
import re
from pathlib import Path

_ENTRYPOINT = Path(__file__).resolve().parents[2] / "entrypoint.sh"


def test_every_uvicorn_launch_caps_websocket_messages():
    script = _ENTRYPOINT.read_text(encoding="utf-8")
    launches = [line for line in script.splitlines() if "uvicorn main:app" in line]
    assert launches
    assert all("--ws-max-size $WS_MAX_SIZE" in line for line in launches)
    limit = int(re.search(r"^WS_MAX_SIZE=(\d+)$", script, re.MULTILINE).group(1))
    # Room for one chat message (~24 KB), nothing like uvicorn's 16 MiB default.
    assert 32 * 1024 <= limit <= 64 * 1024
