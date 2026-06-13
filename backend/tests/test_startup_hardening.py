"""Boot-time hardening guards: placeholder JWT secret, MK_DEBUG-in-prod, gated docs.

The first two guards run at import time (fail-fast), so they are exercised in a
fresh subprocess with a crafted environment — a raise during import must not
corrupt the shared pytest process. The docs-gating assertion reads the already
imported app, which (the suite runs with MK_DEBUG unset) must expose no OpenAPI
routes.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _import_in_subprocess(target: str, env_overrides: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", f"import {target}"],
        cwd=BACKEND_ROOT,
        env={**os.environ, **env_overrides},
        capture_output=True,
        text=True,
    )


def test_placeholder_jwt_secret_refused_at_import():
    result = _import_in_subprocess(
        "core.security",
        {"JWT_SECRET_KEY": "change-me-with-at-least-32-random-bytes"},
    )
    assert result.returncode != 0
    assert "placeholder" in result.stderr.lower()


def test_debug_true_in_production_refused_at_import():
    result = _import_in_subprocess("main", {"MK_DEBUG": "true", "ENV": "production"})
    assert result.returncode != 0
    assert "MK_DEBUG" in result.stderr


def test_debug_true_without_production_boots():
    # MK_DEBUG alone (no ENV=production) must not trip the guard.
    result = _import_in_subprocess("main", {"MK_DEBUG": "true", "ENV": ""})
    assert result.returncode == 0, result.stderr


def test_openapi_docs_disabled_without_debug():
    # The shared suite imports main with MK_DEBUG unset → docs/schema gated off.
    import main

    assert main.app.docs_url is None
    assert main.app.redoc_url is None
    assert main.app.openapi_url is None
