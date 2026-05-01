"""add seasons/episodes columns to media_requests

Revision ID: 014_request_seasons
Revises: 013_demandes_featured
Create Date: 2026-04-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "014_request_seasons"
down_revision: Union[str, None] = "013_demandes_featured"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("media_requests",
        sa.Column("requested_seasons", sa.JSON, nullable=True))
    op.add_column("media_requests",
        sa.Column("requested_by_admin", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    op.drop_column("media_requests", "requested_by_admin")
    op.drop_column("media_requests", "requested_seasons")
