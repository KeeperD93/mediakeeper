"""uvicorn never takes the client address from X-Forwarded-For on its own: every
launch path pins its trusted list to loopback, whatever FORWARDED_ALLOW_IPS says."""
import re
from pathlib import Path

_ENTRYPOINT = Path(__file__).resolve().parents[2] / "entrypoint.sh"


def test_every_uvicorn_launch_pins_the_forwarded_allow_list():
    script = _ENTRYPOINT.read_text(encoding="utf-8")
    launches = [line for line in script.splitlines() if "uvicorn main:app" in line]
    assert launches
    assert all("--forwarded-allow-ips $UVICORN_FORWARDED_IPS" in line for line in launches)
    pinned = re.search(r'^UVICORN_FORWARDED_IPS="([^"]*)"$', script, re.MULTILINE).group(1)
    assert pinned == "127.0.0.1,::1"
