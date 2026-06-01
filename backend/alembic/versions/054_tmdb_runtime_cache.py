"""Add ``tmdb_runtime_cache`` — persistent TMDB runtime cache.

TMDB list endpoints (trending/popular/discover/search) never return a
movie/series runtime — only the per-item detail endpoint does. To show a
duration on every portal poster card without an N+1 detail call per render,
runtimes are resolved once and cached here, keyed by (tmdb_id, media_type).
The table is persistent so the cache is not re-warmed on every boot.

Idempotent create: skip when the table already exists (deployments
bootstrapped via ``Base.metadata.create_all`` already have it).
"""
from alembic import op
import sqlalchemy as sa


revision = "054_tmdb_runtime_cache"
down_revision = "053_user_profile_selected_title"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "tmdb_runtime_cache" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "tmdb_runtime_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.Column("runtime", sa.Integer(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tmdb_id", "media_type", name="uq_tmdb_runtime"),
    )
    op.create_index(
        "ix_tmdb_runtime_cache_tmdb_id", "tmdb_runtime_cache", ["tmdb_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "tmdb_runtime_cache" not in sa.inspect(bind).get_table_names():
        return
    op.drop_index("ix_tmdb_runtime_cache_tmdb_id", table_name="tmdb_runtime_cache")
    op.drop_table("tmdb_runtime_cache")
