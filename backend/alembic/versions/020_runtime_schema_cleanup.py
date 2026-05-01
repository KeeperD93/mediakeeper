"""Move runtime schema patches into Alembic.

Revision ID: 020_runtime_schema_cleanup
Revises: 019_xp_ledger
"""
revision = "020_runtime_schema_cleanup"
down_revision = "019_xp_ledger"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    playback_columns = _column_names(inspector, "playback_sessions")
    if "audio_language" not in playback_columns:
        op.add_column("playback_sessions", sa.Column("audio_language", sa.String(length=50), nullable=True))
    if "subtitle_language" not in playback_columns:
        op.add_column("playback_sessions", sa.Column("subtitle_language", sa.String(length=50), nullable=True))
    if "genres" not in playback_columns:
        op.add_column("playback_sessions", sa.Column("genres", sa.String(length=500), nullable=True))

    health_columns = _column_names(inspector, "healthcheck_results")
    if "series_id" not in health_columns:
        op.add_column("healthcheck_results", sa.Column("series_id", sa.String(length=100), nullable=True))
        health_columns.add("series_id")
    if "season_num" not in health_columns:
        op.add_column("healthcheck_results", sa.Column("season_num", sa.Integer(), nullable=True))
    if "episode_num" not in health_columns:
        op.add_column("healthcheck_results", sa.Column("episode_num", sa.Integer(), nullable=True))

    health_indexes = _index_names(inspector, "healthcheck_results")
    if "ix_hc_series_id" not in health_indexes:
        op.create_index("ix_hc_series_id", "healthcheck_results", ["series_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    health_columns = _column_names(inspector, "healthcheck_results")
    health_indexes = _index_names(inspector, "healthcheck_results")
    if "ix_hc_series_id" in health_indexes:
        op.drop_index("ix_hc_series_id", table_name="healthcheck_results")
    if "episode_num" in health_columns:
        op.drop_column("healthcheck_results", "episode_num")
    if "season_num" in health_columns:
        op.drop_column("healthcheck_results", "season_num")
    if "series_id" in health_columns:
        op.drop_column("healthcheck_results", "series_id")

    playback_columns = _column_names(inspector, "playback_sessions")
    if "genres" in playback_columns:
        op.drop_column("playback_sessions", "genres")
    if "subtitle_language" in playback_columns:
        op.drop_column("playback_sessions", "subtitle_language")
    if "audio_language" in playback_columns:
        op.drop_column("playback_sessions", "audio_language")
