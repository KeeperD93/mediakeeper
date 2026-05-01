"""create doublon tables (ignored + cleanup history)

Revision ID: 003_doublon_tables
Revises: 002_add_language_columns
Create Date: 2026-03-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_doublon_tables"
down_revision: Union[str, None] = "002_add_language_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ignored_doublons",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("doublon_key", sa.String(500), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("ignored_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "doublon_cleanups",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("filename", sa.String(1000), nullable=True),
        sa.Column("size_bytes", sa.BigInteger, default=0),
        sa.Column("action", sa.String(50), default="deleted"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("doublon_cleanups")
    op.drop_table("ignored_doublons")
