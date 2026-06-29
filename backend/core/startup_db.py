"""Database schema-mode resolution, validation, and bootstrap-admin notice.

Pure helpers extracted from ``app_startup``. ``init_db`` (which owns the
``_db_ready`` flag monkeypatched by the test suite) stays in app_startup
and calls these.
"""
import logging
import os

from sqlalchemy import inspect

from constants import env_vars
from core.database import DATABASE_URL
from models.base import Base

logger = logging.getLogger("mediakeeper")


def _schema_mode() -> str:
    """
    Determine how startup handles the DB schema.

    - sqlite test/dev DBs keep ``create_all`` for convenience.
    - Postgres defaults to ``validate`` so runtime no longer masks
      missing Alembic migrations by creating tables on the fly.
    - ``MK_DB_SCHEMA_MODE=create_all`` keeps the old bootstrap
      behaviour explicitly when needed.
    """
    raw = (os.getenv(env_vars.MK_DB_SCHEMA_MODE, "auto").strip().lower() or "auto")
    if raw in {"create_all", "validate"}:
        return raw
    return "create_all" if DATABASE_URL.startswith("sqlite") else "validate"


def _validate_registered_schema(sync_conn) -> None:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables.keys())
    missing = sorted(expected_tables - existing_tables)
    if missing:
        preview = ", ".join(missing[:8])
        if len(missing) > 8:
            preview += ", ..."
        raise RuntimeError(
            "Incomplete DB schema. Missing tables: "
            f"{preview}. Apply Alembic migrations or set MK_DB_SCHEMA_MODE=create_all."
        )


def _emit_bootstrap_admin_credentials(username: str, password: str) -> None:
    """
    Display initial credentials on the console output only
    to avoid persisting them in log files.
    """
    lines = [
        "=" * 60,
        "  ADMIN ACCOUNT CREATED",
        f"  Username: {username}",
        f"  Password: {password}",
        "  You MUST change this password on first login.",
        "  CAPTURE THIS NOW — it is not written to /data and",
        "  cannot be recovered from disk later.",
        "  Lost it? See docs/operations/admin-recovery.md",
        "  (run scripts/reset_admin from a host docker exec).",
        "=" * 60,
    ]
    emitted = False
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            stream = getattr(handler, "stream", None)
            if not stream:
                continue
            for line in lines:
                stream.write(f"{line}\n")
            stream.flush()
            emitted = True

    if not emitted:
        logger.warning("=" * 60)
        logger.warning("  ADMIN ACCOUNT CREATED")
        logger.warning(f"  Username: {username}")
        logger.warning("  Initial password is only available on first startup.")
        logger.warning("  Lost it? See docs/operations/admin-recovery.md")
        logger.warning("=" * 60)
