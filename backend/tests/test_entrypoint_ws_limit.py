"""Every launch path caps WebSocket messages at what one chat frame needs: a
small compressed frame must never inflate to megabytes on the server."""
import re
from pathlib import Path

_ENTRYPOINT = Path(__file__).resolve().parents[2] / "entrypoint.sh"


def test_every_uvicorn_launch_caps_websocket_messages():
    script = _ENTRYPOINT.read_text(encoding="utf-8")
    code = [line for line in script.splitlines() if not line.lstrip().startswith("#")]
    launches = [line for line in code if re.search(r"\buvicorn\b.*\bmain:app\b", line)]
    assert launches
    for line in launches:
        # Exactly one flag, from the shared variable: click keeps the last value given.
        assert re.findall(r'--ws-max-size[ =]+([^\s"]+)', line) == ["$WS_MAX_SIZE"]
    # Every other mention that is not a `$` read writes it (`&&`, `+=`, `readonly`…).
    writes = [line.strip() for line in code if re.search(r"(?<![\w${])WS_MAX_SIZE\b", line)]
    assert len(writes) == 1
    limit = re.fullmatch(r"WS_MAX_SIZE=(\d+)", writes[0])
    assert limit
    # Room for one chat message (~24 KB), nothing like uvicorn's 16 MiB default.
    assert 32 * 1024 <= int(limit.group(1)) <= 64 * 1024
