"""Cache the Emby ``DateCreated`` field on the index for two trophies.

A single column is added to ``emby_tmdb_index`` so the achievement runner
can answer "was this freshly added?" and "has this been on the shelf for
a year?" without a round-trip to Emby per session:

* ``date_created`` (DateTime, timezone-aware, nullable) — already
  returned by ``/Items?Fields=DateCreated``, persisted on every sync.

The column drives ``secret_pilot`` (first viewer within a freshness
window) and ``secret_late`` (started a session at least 1 year after
the file was added). It is filled lazily — rows synced before this
migration stay NULL and are picked up on the next sync pass.

``op.batch_alter_table`` is used so SQLite (CI tests) accepts the
mutation without a manual table rebuild.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "043_emby_tmdb_index_date_created"
down_revision: Union[str, None] = "042_emby_tmdb_index_year_lang"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("emby_tmdb_index")}

    with op.batch_alter_table("emby_tmdb_index") as batch_op:
        if "date_created" not in cols:
            batch_op.add_column(
                sa.Column("date_created", sa.DateTime(timezone=True), nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("emby_tmdb_index")}

    with op.batch_alter_table("emby_tmdb_index") as batch_op:
        if "date_created" in cols:
            batch_op.drop_column("date_created")
