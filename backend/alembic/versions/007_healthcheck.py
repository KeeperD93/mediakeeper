"""create healthcheck_results table

Revision ID: 007_healthcheck
Revises: 005_scheduler_tasks
Create Date: 2026-03-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "007_healthcheck"
down_revision: Union[str, None] = "005_scheduler_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "healthcheck_results",
        sa.Column("id",           sa.Integer,                       primary_key=True, index=True),
        sa.Column("item_id",      sa.String(100),  nullable=False),
        sa.Column("item_name",    sa.String(500),  nullable=False),
        sa.Column("item_type",    sa.String(50),   nullable=False),
        sa.Column("series_name",  sa.String(500),  nullable=True),
        sa.Column("library_name", sa.String(200),  nullable=True),
        sa.Column("issues",       sa.Text,         nullable=False, server_default="[]"),
        sa.Column("severity",     sa.String(20),   nullable=False, server_default="info"),
        sa.Column("file_path",    sa.String(2000), nullable=True),
        sa.Column("scanned_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hc_item_id",  "healthcheck_results", ["item_id"])
    op.create_index("ix_hc_library",  "healthcheck_results", ["library_name"])
    op.create_index("ix_hc_severity", "healthcheck_results", ["severity"])
    op.create_index("ix_hc_scanned",  "healthcheck_results", ["scanned_at"])


def downgrade() -> None:
    op.drop_table("healthcheck_results")
