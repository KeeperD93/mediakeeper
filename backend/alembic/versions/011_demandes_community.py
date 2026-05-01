"""create demandes tables: achievements, user_achievements,
seasonal_events, seasonal_progress, chat_rooms, chat_messages, chat_mutes

Revision ID: 011_demandes_community
Revises: 010_demandes_tickets_news
Create Date: 2026-04-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "011_demandes_community"
down_revision: Union[str, None] = "010_demandes_tickets_news"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- achievements ---
    op.create_table(
        "achievements",
        sa.Column("id",              sa.String(50),    primary_key=True),
        sa.Column("category",        sa.String(30),    nullable=False, index=True),
        sa.Column("name_key",        sa.String(100),   nullable=False),
        sa.Column("description_key", sa.String(100),   nullable=False),
        sa.Column("icon",            sa.String(100),   nullable=False),
        sa.Column("tier",            sa.Integer,       server_default=sa.text("1"), nullable=False),
        sa.Column("xp_reward",       sa.Integer,       server_default=sa.text("10"), nullable=False),
        sa.Column("threshold",       sa.Integer,       server_default=sa.text("1"), nullable=False),
        sa.Column("condition_type",  sa.String(50),    nullable=False),
        sa.Column("next_tier_id",    sa.String(50),    sa.ForeignKey("achievements.id",
                  ondelete="SET NULL"), nullable=True),
        sa.Column("secret",          sa.Boolean,       server_default=sa.text("false"), nullable=False),
        sa.Column("sort_order",      sa.Integer,       server_default=sa.text("0"), nullable=False),
    )

    # --- user_achievements ---
    op.create_table(
        "user_achievements",
        sa.Column("id",             sa.Integer,       primary_key=True, index=True),
        sa.Column("user_id",        sa.Integer,       sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("achievement_id", sa.String(50),    sa.ForeignKey("achievements.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("progress",       sa.Integer,       server_default=sa.text("0"), nullable=False),
        sa.Column("unlocked",       sa.Boolean,       server_default=sa.text("false"), nullable=False),
        sa.Column("unlocked_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("notified",       sa.Boolean,       server_default=sa.text("false"), nullable=False),
    )

    # --- seasonal_events ---
    op.create_table(
        "seasonal_events",
        sa.Column("id",            sa.Integer,       primary_key=True, index=True),
        sa.Column("name",          sa.String(200),   nullable=False),
        sa.Column("description",   sa.Text,          nullable=True),
        sa.Column("start_date",    sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date",      sa.DateTime(timezone=True), nullable=False),
        sa.Column("genre_filter",  sa.JSON,          nullable=True),
        sa.Column("target_count",  sa.Integer,       server_default=sa.text("10"), nullable=False),
        sa.Column("badge_id",      sa.String(50),    sa.ForeignKey("achievements.id",
                  ondelete="SET NULL"), nullable=True),
        sa.Column("created_by",    sa.Integer,       sa.ForeignKey("users.id",
                  ondelete="SET NULL"), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- seasonal_progress ---
    op.create_table(
        "seasonal_progress",
        sa.Column("id",        sa.Integer,       primary_key=True, index=True),
        sa.Column("event_id",  sa.Integer,       sa.ForeignKey("seasonal_events.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id",   sa.Integer,       sa.ForeignKey("users.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("progress",  sa.Integer,       server_default=sa.text("0"), nullable=False),
        sa.Column("completed", sa.Boolean,       server_default=sa.text("false"), nullable=False),
        sa.UniqueConstraint("event_id", "user_id", name="uq_seasonal_progress"),
    )

    # --- chat_rooms ---
    op.create_table(
        "chat_rooms",
        sa.Column("id",                sa.Integer,       primary_key=True, index=True),
        sa.Column("type",              sa.String(20),    nullable=False, index=True),
        sa.Column("name",              sa.String(100),   nullable=False),
        sa.Column("linked_request_id", sa.Integer,       sa.ForeignKey("media_requests.id",
                  ondelete="SET NULL"), nullable=True),
        sa.Column("created_at",        sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- chat_messages ---
    op.create_table(
        "chat_messages",
        sa.Column("id",          sa.Integer,       primary_key=True, index=True),
        sa.Column("room_id",     sa.Integer,       sa.ForeignKey("chat_rooms.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id",     sa.Integer,       sa.ForeignKey("users.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("content",     sa.Text,          nullable=False),
        sa.Column("deleted",     sa.Boolean,       server_default=sa.text("false"), nullable=False),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- chat_mutes ---
    op.create_table(
        "chat_mutes",
        sa.Column("id",          sa.Integer,       primary_key=True, index=True),
        sa.Column("user_id",     sa.Integer,       sa.ForeignKey("users.id",
                  ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("muted_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason",      sa.String(300),   nullable=True),
    )


def downgrade() -> None:
    op.drop_table("chat_mutes")
    op.drop_table("chat_messages")
    op.drop_table("chat_rooms")
    op.drop_table("seasonal_progress")
    op.drop_table("seasonal_events")
    op.drop_table("user_achievements")
    op.drop_table("achievements")
