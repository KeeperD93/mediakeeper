"""
Alembic env.py — migration configuration.
Uses the same connection logic as core/database.py.
"""

import os
import asyncio
from pathlib import Path
from logging.config import fileConfig
from urllib.parse import urlparse, quote

from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import every model so metadata knows about them
from models.base import Base
from models.user import User                    # noqa: F401
from models.settings import Setting             # noqa: F401
from models.seen_alert import SeenAlert         # noqa: F401
from models.playback_stats import PlaybackSession, LibraryCache, PlaybackPauseEvent  # noqa: F401
from models.user_preferences import UserPreference   # noqa: F401
from models.watchlist_scans import WatchlistScan     # noqa: F401
from models.notification_channels import NotificationChannel  # noqa: F401
from models.ignored_duplicate import IgnoredDoublon    # noqa: F401
from models.duplicate_cleanup import DoublonCleanup    # noqa: F401
from models.notification_log import NotificationLog  # noqa: F401
from models.scheduler_task import SchedulerTask      # noqa: F401
from models.healthcheck import HealthCheckResult     # noqa: F401
from models.subtitle_history import SubtitleDownload  # noqa: F401
from models.subtitle_profile import SubtitleProfile  # noqa: F401
from models.security import SecurityAttempt, SecurityBlock  # noqa: F401
# Every portal model is re-exported by models.portal (single source of truth),
# so autogenerate sees the whole schema without a hand-maintained list here.
from models.portal import *  # noqa: F401,F403

config = context.config
if config.config_file_name is not None:
    # ``disable_existing_loggers=False`` keeps the application's loggers
    # alive when Alembic is driven from inside the test suite or from a
    # long-running process. Without this flag, ``fileConfig`` resets
    # every logger created prior to its call (including
    # ``mediakeeper.monitoring`` and friends), which silently swallows
    # records the rest of the test run wants to assert on.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _get_database_url() -> str:
    """Resolve the connection URL (same logic as core/database.py).

    SQLite URLs pass through with the ``aiosqlite`` driver so a test
    suite can drive Alembic against a temporary file without spinning
    up Postgres. Production stays on ``postgresql+asyncpg``.
    """
    raw = os.getenv("DATABASE_URL", "")
    if not raw:
        pg_pwd_file = Path("/data/.pg_password")
        if pg_pwd_file.exists():
            pg_pwd = pg_pwd_file.read_text().strip()
            raw = f"postgresql://mediakeeper:{pg_pwd}@127.0.0.1:5432/mediakeeper_db"
        else:
            raise RuntimeError("DATABASE_URL not set and /data/.pg_password not found.")

    parsed = urlparse(raw)

    if parsed.scheme.startswith("sqlite"):
        if parsed.scheme == "sqlite":
            # Upgrade plain ``sqlite://`` to the async driver so the
            # ``run_migrations_online`` path works unchanged.
            return raw.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return raw

    user = parsed.username or ""
    pwd = parsed.password or ""
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    db = (parsed.path or "/mediakeeper_db").lstrip("/")
    return f"postgresql+asyncpg://{quote(user, safe='')}:{quote(pwd, safe='')}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    """Offline mode: generate SQL without a live connection."""
    _install_offline_inspector()
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _install_offline_inspector() -> None:
    """Let idempotent migrations inspect Alembic's offline mock connection."""
    from sqlalchemy.engine.mock import MockConnection
    from sqlalchemy.inspection import _inspects

    class OfflineInspector:
        def get_table_names(self, *args, **kwargs):
            return []

        def get_columns(self, *args, **kwargs):
            return []

        def get_indexes(self, *args, **kwargs):
            return []

        def get_unique_constraints(self, *args, **kwargs):
            return []

        def get_foreign_keys(self, *args, **kwargs):
            return []

        def has_table(self, *args, **kwargs):
            return False

    @_inspects(MockConnection)
    def _inspect_mock_connection(connection):
        return OfflineInspector()


def do_run_migrations(connection):
    # ──────────────────────────────────────────────────────────────
    # Self-healing ``alembic_version.version_num`` on Postgres.
    #
    # Alembic defaults ``version_num`` to ``VARCHAR(32)``, which trips
    # slug-style revision ids that exceed 32 chars (e.g.
    # ``045_news_scheduling_and_maintenance`` is 35). Both deploy
    # paths are handled idempotently here:
    #   * fresh install — ``CREATE TABLE IF NOT EXISTS`` races ahead
    #     of Alembic's own DDL so the table is born wide enough for
    #     every slug we ship now and in the future.
    #   * existing install on legacy ``VARCHAR(32)`` — ``ALTER COLUMN``
    #     widens to ``VARCHAR(64)``. On PostgreSQL ≥ 9.2 this DDL is
    #     metadata-only (no table rewrite). Already-64 columns no-op.
    #
    # SQLite is skipped: it ignores ``VARCHAR`` length, so local tests
    # and dev DBs are unaffected.
    # ──────────────────────────────────────────────────────────────
    if connection.dialect.name == "postgresql":
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "  version_num VARCHAR(64) NOT NULL, "
            "  CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
            ")"
        ))
        connection.execute(text(
            "ALTER TABLE alembic_version "
            "ALTER COLUMN version_num TYPE VARCHAR(64)"
        ))

    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Online mode: async connection.

    Uses ``connectable.begin()`` (not ``.connect()``) so the whole
    ``run_sync(do_run_migrations)`` block runs inside a transaction that
    asyncpg commits on success. With ``.connect()``, the implicit tx
    triggered by the early DDL widen calls in ``do_run_migrations``
    (the ``alembic_version`` ``VARCHAR(64)`` self-heal) never got an
    explicit ``COMMIT``, and the outer asyncpg transaction silently
    rolled back on connection release — taking every Alembic migration
    from this run down with it. ``.begin()`` commits the whole scope
    atomically, so the widen and the migrations land together.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
