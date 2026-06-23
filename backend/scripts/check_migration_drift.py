"""Fail the build when the SQLAlchemy models drift from the Alembic migrations.

A fresh production install builds its schema from the migrations, never from
``create_all``. A model column added without a matching migration therefore
ships green in the SQLite unit suite yet breaks a real PostgreSQL boot (the
rc.1 ``selected_title`` class of bug). This replays the whole migration chain
against a real PostgreSQL (``DATABASE_URL``) and compares the result against the
models, exiting non-zero on any table/column the migrations do not produce.

Run by the CI ``migration-drift`` job, which provides a throwaway PostgreSQL
service. It is deliberately NOT a pytest test: ``tests/conftest.py`` forces
``DATABASE_URL`` to in-memory SQLite at import, and SQLite cannot replay the
pre-040 chain anyway.
"""
import asyncio
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

from alembic import command  # noqa: E402
from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

# compare_metadata also reports index / constraint / nullable nuances that are
# NOT real drift: an index for ``index=True`` on a primary key, model-named vs
# migration-named indexes, a ``unique=True`` rendered as a unique index vs a
# unique constraint, and nullable-with-server-default timestamps. Only an
# added/removed table or column means a migration is genuinely missing.
_DRIFT_OPS = {"add_table", "remove_table", "add_column", "remove_column"}


async def _model_vs_db(async_url, metadata):
    engine = create_async_engine(async_url)
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(
                lambda c: compare_metadata(MigrationContext.configure(c), metadata)
            )
    finally:
        await engine.dispose()


def main() -> int:
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        print(f"[drift] needs a PostgreSQL DATABASE_URL, got {url or '(unset)'!r}", file=sys.stderr)
        return 2

    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")  # replays the full chain; env.py loads every model

    from models.base import Base  # after upgrade so Base.metadata is fully populated

    async_url = url if "+asyncpg" in url else url.replace("postgresql://", "postgresql+asyncpg://", 1)
    diff = asyncio.run(_model_vs_db(async_url, Base.metadata))
    drift = [d for d in diff if isinstance(d, tuple) and d[0] in _DRIFT_OPS]

    print(f"[drift] compare_metadata: {len(diff)} diffs, {len(drift)} structural (add/remove table/column)")
    if drift:
        print("[drift] FAIL - a model table/column has no migration (or vice-versa):")
        for d in drift:
            print(f"    {d}")
        return 1
    print("[drift] OK - models and migrations agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
