"""create notification_logs table

Revision ID: 004_notification_logs
Revises: 003_doublon_tables
Create Date: 2026-03-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004_notification_logs"
down_revision: Union[str, None] = "003_doublon_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("event_type", sa.String(100), nullable=False, index=True),
        sa.Column("channel", sa.String(50), default="discord"),
        sa.Column("webhook_name", sa.String(200), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), default="sent"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("notification_logs")
