"""Every launch path caps WebSocket messages at what one chat frame needs: a
small compressed frame must never inflate to megabytes on the server."""
import re
from pathlib import Path

_ENTRYPOINT = Path(__file__).resolve().parents[2] / "entrypoint.sh"


def test_every_uvicorn_launch_caps_websocket_messages():
    script = _ENTRYPOINT.read_text(encoding="utf-8")
    launches = [
        line for line in script.splitlines()
        if not line.lstrip().startswith("#") and re.search(r"\buvicorn\b.*\bmain:app\b", line)
    ]
    assert launches
    for line in launches:
        # Exactly one flag, from the shared variable: click keeps the last value given.
        assert re.findall(r'--ws-max-size[ =]+([^\s"]+)', line) == ["$WS_MAX_SIZE"]
    assigned = re.findall(r"^\s*(?:export\s+)?WS_MAX_SIZE=(.*)$", script, re.MULTILINE)
    assert len(assigned) == 1
    # Room for one chat message (~24 KB), nothing like uvicorn's 16 MiB default.
    assert 32 * 1024 <= int(assigned[0]) <= 64 * 1024
