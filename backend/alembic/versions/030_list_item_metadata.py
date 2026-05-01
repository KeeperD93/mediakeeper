"""Snapshot TMDB metadata (title, poster_url, year) on user_list_items
so lists render without a per-item TMDB lookup.
"""
from alembic import op
import sqlalchemy as sa

revision = "030_list_item_metadata"
down_revision = "028_request_backdrop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("user_list_items")}
    if "title" not in existing:
        op.add_column("user_list_items",
                      sa.Column("title", sa.String(500), nullable=True))
    if "poster_url" not in existing:
        op.add_column("user_list_items",
                      sa.Column("poster_url", sa.String(500), nullable=True))
    if "year" not in existing:
        op.add_column("user_list_items",
                      sa.Column("year", sa.Integer, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("user_list_items")}
    if "year" in existing:
        op.drop_column("user_list_items", "year")
    if "poster_url" in existing:
        op.drop_column("user_list_items", "poster_url")
    if "title" in existing:
        op.drop_column("user_list_items", "title")
