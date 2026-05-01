"""create scheduler_tasks table

Revision ID: 005_scheduler_tasks
Revises: 004_notification_logs
Create Date: 2026-03-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005_scheduler_tasks"
down_revision: Union[str, None] = "004_notification_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduler_tasks",
        sa.Column("id",           sa.Integer,                       primary_key=True, index=True),
        sa.Column("key",          sa.String(100),  nullable=False,  unique=True, index=True),
        sa.Column("label",        sa.String(200),  nullable=False),
        sa.Column("enabled",      sa.Boolean,      default=True),
        sa.Column("interval_sec", sa.Integer,      nullable=False),   # intervalle en secondes
        sa.Column("last_run",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status",  sa.String(20),   nullable=True),    # ok | error | running
        sa.Column("last_error",   sa.Text,         nullable=True),
        sa.Column("run_count",    sa.Integer,      default=0),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("scheduler_tasks")
