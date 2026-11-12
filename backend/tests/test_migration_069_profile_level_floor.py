"""Migration 069: a profile left at level 0 is raised to level 1, the others are untouched."""
import pytest
import sqlalchemy as sa
from alembic import command

from models.base import Base
from tests._migration_helpers import alembic_db_at

REVISION = "069_profile_level_floor"
PREVIOUS = "068_unlinked_profiles_local"
RAISED = {"alice": 1, "bob": 1, "carol": 5}


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    with alembic_db_at(PREVIOUS, workspace_tmp_path, monkeypatch) as db:
        yield db


def _add_profiles(engine) -> None:
    tables = Base.metadata.tables
    with engine.begin() as conn:
        for name, level, xp in (("alice", 0, 20), ("bob", 1, 0), ("carol", 5, 1500)):
            user_id = conn.execute(sa.insert(tables["users"]).values(
                username=name, hashed_password="x", is_active=True, must_change_password=False,
            )).inserted_primary_key[0]
            conn.execute(sa.insert(tables["user_profiles"]).values(
                user_id=user_id, display_name=name, level=level, xp=xp,
            ))


def _levels(engine) -> dict[str, int]:
    profiles = Base.metadata.tables["user_profiles"]
    with engine.connect() as conn:
        return dict(conn.execute(sa.select(profiles.c.display_name, profiles.c.level)).all())


def test_upgrade_raises_only_the_profiles_at_level_0(alembic_db):
    cfg, engine = alembic_db
    _add_profiles(engine)

    command.upgrade(cfg, REVISION)

    assert _levels(engine) == RAISED


def test_downgrade_keeps_the_levels(alembic_db):
    cfg, engine = alembic_db
    _add_profiles(engine)
    command.upgrade(cfg, REVISION)

    command.downgrade(cfg, PREVIOUS)

    assert _levels(engine) == RAISED
