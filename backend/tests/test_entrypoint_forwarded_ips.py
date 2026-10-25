"""uvicorn takes the client address from X-Forwarded-For only for a loopback peer:
every launch path pins its trusted list, whatever FORWARDED_ALLOW_IPS says."""
import re
from pathlib import Path

_ENTRYPOINT = Path(__file__).resolve().parents[2] / "entrypoint.sh"


def test_every_uvicorn_launch_pins_the_forwarded_allow_list():
    script = _ENTRYPOINT.read_text(encoding="utf-8")
    launches = [
        line for line in script.splitlines()
        if not line.lstrip().startswith("#") and re.search(r"\buvicorn\b.*\bmain:app\b", line)
    ]
    assert launches
    for line in launches:
        # Exactly one flag, from the pinned variable: click keeps the last value given.
        assert re.findall(r'--forwarded-allow-ips[ =]+([^\s"]+)', line) == ["$UVICORN_FORWARDED_IPS"]
    assigned = re.findall(r"^\s*(?:export\s+)?UVICORN_FORWARDED_IPS=(.*)$", script, re.MULTILINE)
    assert assigned == ['"127.0.0.1,::1"']
