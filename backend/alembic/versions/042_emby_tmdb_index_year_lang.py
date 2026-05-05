"""Cache TMDB metadata on the Emby↔TMDB index for achievements.

Two columns are added to ``emby_tmdb_index`` so the achievement runner
can reason about a media's release decade and original language without
calling TMDB on every check:

* ``production_year`` (SmallInteger, nullable) — already returned by
  Emby's ``/Items?Fields=ProductionYear``, persisted on every sync.
* ``original_language`` (String(2), nullable) — ISO 639-1 code from
  TMDB ``/movie/{id}`` or ``/tv/{id}``. Backfilled lazily by the next
  sync run for rows where the column is still NULL.

``op.batch_alter_table`` is used so SQLite (CI tests) accepts the
mutation without a manual table rebuild.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "042_emby_tmdb_index_year_lang"
down_revision: Union[str, None] = "041_fk_consumer_set_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("emby_tmdb_index")}

    with op.batch_alter_table("emby_tmdb_index") as batch_op:
        if "production_year" not in cols:
            batch_op.add_column(
                sa.Column("production_year", sa.SmallInteger(), nullable=True)
            )
        if "original_language" not in cols:
            batch_op.add_column(
                sa.Column("original_language", sa.String(length=2), nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("emby_tmdb_index")}

    with op.batch_alter_table("emby_tmdb_index") as batch_op:
        if "original_language" in cols:
            batch_op.drop_column("original_language")
        if "production_year" in cols:
            batch_op.drop_column("production_year")
