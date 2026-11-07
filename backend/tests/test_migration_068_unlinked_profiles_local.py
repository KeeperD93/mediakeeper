"""Migration 068: a profile never linked to a media-server user is relabelled local."""
import pytest
import sqlalchemy as sa
from alembic import command

from models.base import Base
from tests._migration_helpers import alembic_db_at

REVISION = "068_unlinked_profiles_local"
PREVIOUS = "067_drop_can_earn_xp_offline"
# Only an "emby" profile without an id changes, whether its label came from the
# column default or was set.
RELABELLED = {"admin": "local", "alice": "local", "bob": "emby", "carol": "local", "dave": "local"}


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    with alembic_db_at(PREVIOUS, workspace_tmp_path, monkeypatch) as db:
        yield db


def _add_profile(conn, name: str, *, source: str | None, emby_id: str | None) -> None:
    tables = Base.metadata.tables
    user_id = conn.execute(sa.insert(tables["users"]).values(
        username=name, hashed_password="x", is_active=True, must_change_password=False,
    )).inserted_primary_key[0]
    # No source given: the column default, as on the profiles 035 found.
    extra = {} if source is None else {"source": source}
    conn.execute(sa.insert(tables["user_profiles"]).values(
        user_id=user_id, display_name=name, emby_user_id=emby_id, **extra,
    ))


def _sources(engine) -> dict[str, str]:
    profiles = Base.metadata.tables["user_profiles"]
    with engine.connect() as conn:
        return dict(conn.execute(sa.select(profiles.c.display_name, profiles.c.source)).all())


def _add_every_kind(engine) -> None:
    with engine.begin() as conn:
        _add_profile(conn, "admin", source=None, emby_id=None)
        _add_profile(conn, "alice", source="emby", emby_id=None)
        _add_profile(conn, "bob", source="emby", emby_id="emby-bob")
        _add_profile(conn, "carol", source="local", emby_id=None)
        _add_profile(conn, "dave", source="local", emby_id="emby-dave")


def test_upgrade_relabels_only_the_unlinked_emby_profiles(alembic_db):
    cfg, engine = alembic_db
    _add_every_kind(engine)

    command.upgrade(cfg, REVISION)

    assert _sources(engine) == RELABELLED


def test_downgrade_keeps_the_labels(alembic_db):
    cfg, engine = alembic_db
    _add_every_kind(engine)
    command.upgrade(cfg, REVISION)

    command.downgrade(cfg, PREVIOUS)

    assert _sources(engine) == RELABELLED
