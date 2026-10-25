"""uvicorn takes the client address from X-Forwarded-For only for a loopback peer:
every launch path pins its trusted list, whatever FORWARDED_ALLOW_IPS or
UVICORN_FORWARDED_ALLOW_IPS says."""
import re
from pathlib import Path

_ENTRYPOINT = Path(__file__).resolve().parents[2] / "entrypoint.sh"


def test_every_uvicorn_launch_pins_the_forwarded_allow_list():
    script = _ENTRYPOINT.read_text(encoding="utf-8")
    code = [line for line in script.splitlines() if not line.lstrip().startswith("#")]
    launches = [line for line in code if re.search(r"\buvicorn\b.*\bmain:app\b", line)]
    assert launches
    for line in launches:
        # Exactly one flag, from the pinned variable: click keeps the last value given.
        assert re.findall(r'--forwarded-allow-ips[ =]+([^\s"]+)', line) == ["$UVICORN_FORWARDED_IPS"]
    # Every other mention that is not a `$` read writes it (`&&`, `+=`, `readonly`…).
    writes = [line.strip() for line in code if re.search(r"(?<![\w${])UVICORN_FORWARDED_IPS\b", line)]
    assert writes == ['UVICORN_FORWARDED_IPS="127.0.0.1,::1"']
