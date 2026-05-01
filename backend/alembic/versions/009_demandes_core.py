"""create demandes core tables: user_profiles, emby_tmdb_index,
media_requests, request_votes, request_quotas

Revision ID: 009_demandes_core
Revises: 008_subtitle_tables
Create Date: 2026-04-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "009_demandes_core"
down_revision: Union[str, None] = "008_subtitle_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- user_profiles ---
    op.create_table(
        "user_profiles",
        sa.Column("id",               sa.Integer,       primary_key=True, index=True),
        sa.Column("user_id",          sa.Integer,       sa.ForeignKey("users.id", ondelete="CASCADE"),
                  unique=True, nullable=False, index=True),
        sa.Column("display_name",     sa.String(50),    nullable=False),
        sa.Column("avatar_url",       sa.String(500),   nullable=True),
        sa.Column("bio",              sa.Text,          nullable=True),
        sa.Column("favorite_genres",  sa.JSON,          nullable=True),
        sa.Column("level",            sa.Integer,       server_default=sa.text("1"), nullable=False),
        sa.Column("xp",              sa.Integer,        server_default=sa.text("0"), nullable=False),
        sa.Column("selected_badges",  sa.JSON,          nullable=True),
        sa.Column("is_public",        sa.Boolean,       server_default=sa.text("true"), nullable=False),
        sa.Column("role",             sa.String(20),    server_default="viewer", nullable=False),
        sa.Column("language",         sa.String(10),    server_default="fr", nullable=False),
        sa.Column("chat_enabled",     sa.Boolean,       server_default=sa.text("true"), nullable=False),
        sa.Column("chat_muted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("account_active",   sa.Boolean,       server_default=sa.text("true"), nullable=False),
        sa.Column("forced_public",    sa.Boolean,       nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- emby_tmdb_index ---
    op.create_table(
        "emby_tmdb_index",
        sa.Column("id",             sa.Integer,       primary_key=True, index=True),
        sa.Column("emby_item_id",   sa.String(64),    nullable=False, unique=True, index=True),
        sa.Column("tmdb_id",        sa.Integer,       nullable=False, index=True),
        sa.Column("media_type",     sa.String(20),    nullable=False),
        sa.Column("title",          sa.String(500),   nullable=True),
        sa.Column("updated_at",     sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- media_requests ---
    op.create_table(
        "media_requests",
        sa.Column("id",             sa.Integer,       primary_key=True, index=True),
        sa.Column("user_id",        sa.Integer,       sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("tmdb_id",        sa.Integer,       nullable=False, index=True),
        sa.Column("media_type",     sa.String(20),    nullable=False),
        sa.Column("title",          sa.String(500),   nullable=False),
        sa.Column("year",           sa.Integer,       nullable=True),
        sa.Column("poster_url",     sa.String(500),   nullable=True),
        sa.Column("status",         sa.String(20),    server_default="pending",
                  nullable=False, index=True),
        sa.Column("reject_reason",  sa.Text,          nullable=True),
        sa.Column("approved_by",    sa.Integer,       sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("auto_approved",  sa.Boolean,       server_default=sa.text("false"), nullable=False),
        sa.Column("vote_count",     sa.Integer,       server_default=sa.text("0"), nullable=False),
        sa.Column("created_at",     sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",     sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- request_votes ---
    op.create_table(
        "request_votes",
        sa.Column("id",           sa.Integer,       primary_key=True, index=True),
        sa.Column("request_id",   sa.Integer,       sa.ForeignKey("media_requests.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("user_id",      sa.Integer,       sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "request_id", name="uq_request_vote"),
    )

    # --- request_quotas ---
    op.create_table(
        "request_quotas",
        sa.Column("id",           sa.Integer,       primary_key=True, index=True),
        sa.Column("user_id",      sa.Integer,       sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, unique=True, index=True),
        sa.Column("month",        sa.String(7),     nullable=False),
        sa.Column("used",         sa.Integer,       server_default=sa.text("0"), nullable=False),
        sa.Column("max_allowed",  sa.Integer,       server_default=sa.text("5"), nullable=False),
        sa.Column("mode",         sa.String(20),    server_default="fixed", nullable=False),
        sa.Column("unlimited",    sa.Boolean,       server_default=sa.text("false"), nullable=False),
        sa.Column("auto_approve", sa.Boolean,       server_default=sa.text("false"), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("request_quotas")
    op.drop_table("request_votes")
    op.drop_table("media_requests")
    op.drop_table("emby_tmdb_index")
    op.drop_table("user_profiles")
