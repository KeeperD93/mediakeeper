"""create demandes tables: tickets, ticket_replies, news, news_reads

Revision ID: 010_demandes_tickets_news
Revises: 009_demandes_core
Create Date: 2026-04-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "010_demandes_tickets_news"
down_revision: Union[str, None] = "009_demandes_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- tickets ---
    op.create_table(
        "tickets",
        sa.Column("id",            sa.Integer,       primary_key=True, index=True),
        sa.Column("user_id",       sa.Integer,       sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("emby_item_id",  sa.String(64),    nullable=True),
        sa.Column("tmdb_id",       sa.Integer,       nullable=True),
        sa.Column("media_title",   sa.String(500),   nullable=False),
        sa.Column("media_type",    sa.String(20),    nullable=False),
        sa.Column("issue_type",    sa.String(30),    nullable=False, index=True),
        sa.Column("priority",      sa.String(20),    server_default="minor", nullable=False),
        sa.Column("description",   sa.Text,          nullable=False),
        sa.Column("status",        sa.String(20),    server_default="open",
                  nullable=False, index=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- ticket_replies ---
    op.create_table(
        "ticket_replies",
        sa.Column("id",          sa.Integer,       primary_key=True, index=True),
        sa.Column("ticket_id",   sa.Integer,       sa.ForeignKey("tickets.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("user_id",     sa.Integer,       sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("content",     sa.Text,          nullable=False),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- news ---
    op.create_table(
        "news",
        sa.Column("id",              sa.Integer,       primary_key=True, index=True),
        sa.Column("author_id",       sa.Integer,       sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("title",           sa.String(300),   nullable=False),
        sa.Column("content",         sa.Text,          nullable=False),
        sa.Column("image_url",       sa.String(500),   nullable=True),
        sa.Column("type",            sa.String(30),    server_default="announcement",
                  nullable=False, index=True),
        sa.Column("pinned",          sa.Boolean,       server_default=sa.text("false"), nullable=False),
        sa.Column("notify_discord",  sa.Boolean,       server_default=sa.text("false"), nullable=False),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- news_reads ---
    op.create_table(
        "news_reads",
        sa.Column("id",        sa.Integer,       primary_key=True, index=True),
        sa.Column("news_id",   sa.Integer,       sa.ForeignKey("news.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("user_id",   sa.Integer,       sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("read_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("dismissed", sa.Boolean,       server_default=sa.text("false"), nullable=False),
        sa.UniqueConstraint("news_id", "user_id", name="uq_news_read"),
    )


def downgrade() -> None:
    op.drop_table("news_reads")
    op.drop_table("news")
    op.drop_table("ticket_replies")
    op.drop_table("tickets")
