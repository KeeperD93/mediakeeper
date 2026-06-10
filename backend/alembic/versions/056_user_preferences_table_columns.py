"""Add user_preferences.table_columns — per-user resizable table column widths.

Stores a JSON map ``{table_id: [widths]}`` so any resizable table persists its
column widths per user. Additive and nullable (existing rows read as NULL ->
empty map), so no data backfill is needed. ``op.add_column`` runs natively on
both PostgreSQL and SQLite; the inspector guard keeps the upgrade idempotent.
"""
from alembic import op
import sqlalchemy as sa


revision = "056_user_preferences_table_columns"
down_revision = "055_user_profile_language_nullable"
branch_labels = None
depends_on = None


def _has_table_columns(bind) -> bool:
    cols = {c["name"] for c in sa.inspect(bind).get_columns("user_preferences")}
    return "table_columns" in cols


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table_columns(bind):
        op.add_column(
            "user_preferences",
            sa.Column("table_columns", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table_columns(bind):
        with op.batch_alter_table("user_preferences") as batch:
            batch.drop_column("table_columns")
