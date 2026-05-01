"""chat reports table

Revision ID: 015_chat_reports
Revises: 014_request_seasons
Create Date: 2026-04-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "015_chat_reports"
down_revision: Union[str, None] = "014_request_seasons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "chat_reports" in inspector.get_table_names():
        return

    op.create_table(
        "chat_reports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "message_id",
            sa.Integer,
            sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "reporter_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column(
            "handled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "chat_reports" in inspector.get_table_names():
        op.drop_table("chat_reports")
