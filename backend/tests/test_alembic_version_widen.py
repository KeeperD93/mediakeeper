"""Self-healing ``alembic_version.version_num`` widen — env.py guard.

Some of our slug-style revision ids (e.g. ``045_news_scheduling_and_maintenance``)
exceed the legacy Alembic default of ``VARCHAR(32)`` and trip Postgres
on deploy. ``backend/alembic/env.py:do_run_migrations`` therefore widens
the column to ``VARCHAR(64)`` ahead of ``context.configure(...)`` on
Postgres only — SQLite is skipped entirely (it ignores ``VARCHAR``
length).

These tests assert:
* Postgres path issues ``CREATE TABLE IF NOT EXISTS`` then ``ALTER TABLE``,
  in that order, before ``context.configure`` runs.
* SQLite path issues no DDL at all before ``context.configure``.
* A real live SQLite connection completes without raising and without
  ever triggering the Postgres branch.
"""
import importlib.util
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa

from alembic import context as alembic_context


BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_ROOT / "alembic" / "env.py"


def _load_env_module():
    """Import ``backend/alembic/env.py`` as a standalone module.

    Module-level execution of env.py runs ``run_migrations_offline`` or
    ``run_migrations_online`` against the live Alembic context — neither
    is wanted in unit tests. We stub the four ``alembic.context`` entry
    points and ``is_offline_mode`` so the load completes without side
    effects, then return the freshly imported module.
    """
    spec = importlib.util.spec_from_file_location(
        "mediakeeper_alembic_env_under_test", ENV_PATH
    )
    module = importlib.util.module_from_spec(spec)

    @contextmanager
    def _noop_ctx():
        yield

    fake_config = MagicMock(config_file_name=None)

    with patch.object(alembic_context, "is_offline_mode", return_value=True), \
         patch.object(alembic_context, "configure"), \
         patch.object(alembic_context, "begin_transaction", side_effect=_noop_ctx), \
         patch.object(alembic_context, "run_migrations"), \
         patch.object(alembic_context, "config", fake_config, create=True):
        spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def env_module():
    return _load_env_module()


@pytest.fixture
def patched_context(monkeypatch, env_module):
    """Stub Alembic's context state machine for isolated env.py runs."""
    calls: list[str] = []

    def _configure(**_kwargs):
        calls.append("configure")

    @contextmanager
    def _begin_transaction():
        calls.append("begin_transaction")
        yield

    def _run_migrations():
        calls.append("run_migrations")

    monkeypatch.setattr(env_module.context, "configure", _configure)
    monkeypatch.setattr(env_module.context, "begin_transaction", _begin_transaction)
    monkeypatch.setattr(env_module.context, "run_migrations", _run_migrations)
    return calls


def test_postgres_widens_alembic_version_before_configure(env_module, patched_context):
    """Postgres path must run CREATE TABLE IF NOT EXISTS then ALTER, in order, before configure."""
    executed: list[str] = []

    def _execute(stmt):
        executed.append(str(stmt))

    conn = MagicMock(name="pg_connection")
    conn.dialect.name = "postgresql"
    conn.execute.side_effect = _execute

    env_module.do_run_migrations(conn)

    assert len(executed) == 2, (
        "Expected exactly two DDL statements on Postgres "
        f"(CREATE + ALTER), got {len(executed)}: {executed!r}"
    )
    create_stmt, alter_stmt = executed

    assert "CREATE TABLE IF NOT EXISTS alembic_version" in create_stmt
    assert "VARCHAR(64)" in create_stmt
    assert "ALTER TABLE alembic_version" in alter_stmt
    assert "ALTER COLUMN version_num TYPE VARCHAR(64)" in alter_stmt

    assert patched_context == ["configure", "begin_transaction", "run_migrations"], (
        "DDL must precede context.configure; configure must run before begin_transaction/run_migrations"
    )

    assert "CREATE TABLE" in executed[0], "CREATE must precede ALTER (order matters)"
    assert "ALTER TABLE" in executed[1], "ALTER must follow CREATE (order matters)"


def test_sqlite_skips_widen_block(env_module, patched_context):
    """SQLite path must not issue any DDL before configure."""
    conn = MagicMock(name="sqlite_connection")
    conn.dialect.name = "sqlite"

    env_module.do_run_migrations(conn)

    conn.execute.assert_not_called()
    assert patched_context == ["configure", "begin_transaction", "run_migrations"]


def test_sqlite_integration_smoke(env_module, patched_context, tmp_path):
    """Live SQLite connection: no exception, no Postgres DDL leaked."""
    engine = sa.create_engine(f"sqlite:///{(tmp_path / 'smoke.sqlite').as_posix()}", future=True)
    with engine.connect() as conn:
        assert conn.dialect.name == "sqlite"
        env_module.do_run_migrations(conn)
        result = conn.execute(sa.text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        )).first()
        assert result is None, (
            "SQLite branch must not create alembic_version — Alembic itself "
            "owns that DDL on the SQLite path."
        )
    engine.dispose()
