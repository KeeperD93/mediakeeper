"""A PUID change, or its removal, must not cut the app off its own files: the
secrets go back to the runtime user at every start, and a store that ignores
ownership changes stops the start with a message that says why."""
import re
from pathlib import Path

_ENTRYPOINT = Path(__file__).resolve().parents[2] / "entrypoint.sh"
# The secrets are the files the script writes with a single `>`.
_SECRET_WRITE = re.compile(r'(?<!>)>\s*"\$(\w+)"')


def _code() -> list[str]:
    script = _ENTRYPOINT.read_text(encoding="utf-8")
    return [line for line in script.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def _remap_end(code: list[str]) -> int:
    remap = next(i for i, line in enumerate(code) if line.startswith('if [ "$PUID" -ne 0 ]'))
    return code.index("fi", remap)


def test_every_generated_secret_goes_back_to_the_runtime_user_whatever_puid():
    code = _code()
    written = {name for line in code for name in _SECRET_WRITE.findall(line)}
    assert written
    loops = [i for i, line in enumerate(code) if line.startswith("for secret in ")]
    assert len(loops) == 1
    assert written <= set(re.findall(r'"\$(\w+)"', code[loops[0]]))
    # After the remap block closes, so the loop also runs when PUID is unset.
    assert loops[0] > _remap_end(code)
    body = [line.strip() for line in code[loops[0]:code.index("done", loops[0])]]
    guard = body.index('if [ -f "$secret" ] && [ ! -L "$secret" ]; then')
    chown = body.index('chown mkuser:users "$secret" 2>/dev/null || true')
    chmod = body.index('chmod 600 "$secret" 2>/dev/null || true')
    assert guard < chown < chmod < body.index("fi", guard)


def test_postgres_data_dir_ownership_is_checked_before_any_secret_is_written():
    code = _code()
    check = code.index('if [ "$PG_DATA_OWNER" != "$(id -u postgres)" ]; then')
    assert _remap_end(code) < check
    assert check < next(i for i, line in enumerate(code) if _SECRET_WRITE.search(line))
    # `|| true`: a refused chown must reach the explanation, not stop on `set -e`.
    assert code[check - 2] == 'chown postgres:postgres "$PG_DATA" 2>/dev/null || true'
    # -L like PostgreSQL, which checks the directory a link points to.
    assert code[check - 1] == 'PG_DATA_OWNER=$(stat -L -c %u "$PG_DATA")'
    assert "exit 1" in [line.strip() for line in code[check:code.index("fi", check)]]
