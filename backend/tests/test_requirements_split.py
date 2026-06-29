"""Guard: test-only tooling must not leak into the runtime requirements (#423).

The production image installs ``requirements.txt`` alone, so pytest/aiosqlite
living there would ship into the public image. This pins the split so a future
edit can't silently reintroduce them.
"""
from __future__ import annotations

from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_RUNTIME = _BACKEND / "requirements.txt"
_DEV = _BACKEND / "requirements-dev.txt"

_TEST_ONLY = {"pytest", "pytest-asyncio", "pytest-cov", "pytest-randomly", "aiosqlite"}


def _names(path: Path) -> set[str]:
    names: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-")):
            continue
        # "pkg==1.2.3" / "pkg[extra]==1.2.3" -> "pkg"
        names.add(line.split("==")[0].split("[")[0].strip().lower())
    return names


def test_runtime_requirements_have_no_test_tooling():
    leaked = _names(_RUNTIME) & _TEST_ONLY
    assert not leaked, f"test-only deps must move to requirements-dev.txt: {leaked}"


def test_dev_requirements_carry_the_test_tooling():
    missing = _TEST_ONLY - _names(_DEV)
    assert not missing, f"requirements-dev.txt is missing test deps: {missing}"
