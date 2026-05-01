"""create featured_heroes table for manual hero selection

Revision ID: 013_demandes_featured
Revises: 012_demandes_social
Create Date: 2026-04-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "013_demandes_featured"
down_revision: Union[str, None] = "012_demandes_social"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "featured_heroes",
        sa.Column("id",          sa.Integer,       primary_key=True, index=True),
        sa.Column("tmdb_id",     sa.Integer,       nullable=False),
        sa.Column("media_type",  sa.String(20),    nullable=False),
        sa.Column("title",       sa.String(500),   nullable=False),
        sa.Column("overview",    sa.Text,          nullable=True),
        sa.Column("poster_url",  sa.String(500),   nullable=True),
        sa.Column("backdrop",    sa.String(500),   nullable=True),
        sa.Column("vote",        sa.Float,         nullable=True),
        sa.Column("year",        sa.String(10),    nullable=True),
        sa.Column("sort_order",  sa.Integer,       server_default=sa.text("0"), nullable=False),
        sa.Column("active",      sa.Boolean,       server_default=sa.text("true"), nullable=False),
        sa.Column("added_by",    sa.Integer,       sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("featured_heroes")
