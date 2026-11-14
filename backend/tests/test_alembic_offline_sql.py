"""Offline SQL (``alembic upgrade A:B --sql``) of the migrations that inspect
the schema or read rows, rendered for PostgreSQL.

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


def test_offline_sql_renders_067():
    sql = _render("066_last_login_from_sign_ins:067_drop_can_earn_xp_offline")
    assert "ALTER TABLE user_profiles DROP COLUMN can_earn_xp_offline" in sql


def test_offline_sql_renders_069():
    sql = _render("068_unlinked_profiles_local:069_profile_level_floor")
    assert "UPDATE user_profiles SET level = 1 WHERE level < 1" in sql


def test_offline_sql_renders_071_without_reading_the_articles():
    sql = _render("070_profile_onboarding:071_help_seed_rewrite")
    assert "SET version_num='071_help_seed_rewrite'" in sql
    assert "help_article_translations" not in sql


def test_offline_sql_renders_the_072_schema_steps():
    sql = _render("071_help_seed_rewrite:072_display_name_keys")
    assert "ALTER TABLE user_profiles ADD COLUMN display_name_key TEXT" in sql
    assert "ALTER TABLE user_profiles ADD COLUMN display_name_skeleton TEXT" in sql
    assert "DROP INDEX IF EXISTS ix_user_profiles_display_name_lower" in sql
    assert "CREATE UNIQUE INDEX uq_user_profiles_display_name_key ON user_profiles (display_name_key)" in sql
    assert "CREATE INDEX ix_user_profiles_display_name_skeleton ON user_profiles (display_name_skeleton)" in sql
    assert "FROM user_profiles" not in sql
