"""Migration 067: ``user_profiles.can_earn_xp_offline`` goes, every account earns."""
import pytest
import sqlalchemy as sa
from alembic import command

from tests._migration_helpers import alembic_db_at

REVISION = "067_drop_can_earn_xp_offline"
PREVIOUS = "066_last_login_from_sign_ins"


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    with alembic_db_at(PREVIOUS, workspace_tmp_path, monkeypatch) as db:
        yield db


def _columns(engine) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns("user_profiles")}


def test_the_column_goes_and_comes_back_false(alembic_db):
    cfg, engine = alembic_db
    command.upgrade(cfg, REVISION)  # built from the models: nothing to drop
    command.downgrade(cfg, PREVIOUS)
    assert "can_earn_xp_offline" in _columns(engine)
    with engine.begin() as conn:
        user_id = conn.execute(sa.text(
            "INSERT INTO users (username, hashed_password, is_active, must_change_password) "
            "VALUES ('alice', 'x', 1, 0) RETURNING id"
        )).scalar_one()
        conn.execute(sa.text(
            "INSERT INTO user_profiles (user_id, display_name) VALUES (:id, 'Alice')"
        ), {"id": user_id})
        assert conn.execute(sa.text("SELECT can_earn_xp_offline FROM user_profiles")).scalar_one() in (0, False)

    command.upgrade(cfg, REVISION)
    assert "can_earn_xp_offline" not in _columns(engine)
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT display_name FROM user_profiles")).scalar_one() == "Alice"
