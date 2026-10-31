"""Offline SQL (``alembic upgrade A:B --sql``) of the migrations that read
check constraints on PostgreSQL.

Rendered in a child process: env.py registers an inspector for SQLAlchemy's
mock connection, which another test module already registers under its own
module name, and SQLAlchemy refuses a second owner.
"""
import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
# Offline mode never connects: only the dialect of this URL matters.
PG_URL = "postgresql://user:pass@localhost:5432/db"


def _render(revisions: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revisions, "--sql"],
        cwd=BACKEND_ROOT,
        env={**os.environ, "DATABASE_URL": PG_URL, "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout


def test_offline_sql_renders_the_058_check_constraints():
    sql = _render("057_request_quota_auto_mode:058_security_bool_check_constraints")
    assert "ADD CONSTRAINT ck_security_attempts_success_bool CHECK (success IN (0, 1))" in sql
    assert "ADD CONSTRAINT ck_security_blocks_permanent_bool CHECK (permanent IN (0, 1))" in sql


def test_offline_sql_renders_064():
    sql = _render("063_request_archiving:064_security_cleared_and_automatic")
    assert "ALTER TABLE security_attempts ADD COLUMN cleared_at" in sql
    assert "ALTER TABLE security_blocks ADD COLUMN automatic INTEGER DEFAULT '0' NOT NULL" in sql
    assert "ADD CONSTRAINT ck_security_blocks_automatic_bool CHECK (automatic IN (0, 1))" in sql
    assert "UPDATE security_blocks SET automatic = 1" in sql
