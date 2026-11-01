"""Shared setup for the migration tests: a SQLite file built from the current
models and stamped at the revision before the one under test."""
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from models.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def alembic_db_at(previous: str, tmp_dir: Path, monkeypatch) -> Iterator[tuple[Config, sa.Engine]]:
    """Yield the Alembic config and engine of a fresh database stamped at ``previous``."""
    sync_url = f"sqlite:///{(tmp_dir / 'alembic.sqlite').as_posix()}"
    engine = sa.create_engine(sync_url, future=True)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("DATABASE_URL", sync_url)
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.stamp(cfg, previous)
    try:
        yield cfg, engine
    finally:
        engine.dispose()
