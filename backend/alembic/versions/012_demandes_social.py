"""create demandes tables: user_lists, user_list_items, user_ratings,
user_rating_likes, release_reminders, watch_parties, watch_party_participants

Revision ID: 012_demandes_social
Revises: 011_demandes_community
Create Date: 2026-04-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "012_demandes_social"
down_revision: Union[str, None] = "011_demandes_community"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- user_lists ---
    op.create_table(
        "user_lists",
        sa.Column("id",          sa.Integer,       primary_key=True, index=True),
        sa.Column("user_id",     sa.Integer,       sa.ForeignKey("users.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name",        sa.String(200),   nullable=False),
        sa.Column("description", sa.Text,          nullable=True),
        sa.Column("is_public",   sa.Boolean,       server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order",  sa.Integer,       server_default=sa.text("0"), nullable=False),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- user_list_items ---
    op.create_table(
        "user_list_items",
        sa.Column("id",          sa.Integer,       primary_key=True, index=True),
        sa.Column("list_id",     sa.Integer,       sa.ForeignKey("user_lists.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tmdb_id",     sa.Integer,       nullable=False),
        sa.Column("media_type",  sa.String(20),    nullable=False),
        sa.Column("added_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("list_id", "tmdb_id", "media_type", name="uq_list_item"),
    )

    # --- user_ratings ---
    op.create_table(
        "user_ratings",
        sa.Column("id",          sa.Integer,       primary_key=True, index=True),
        sa.Column("user_id",     sa.Integer,       sa.ForeignKey("users.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tmdb_id",     sa.Integer,       nullable=False, index=True),
        sa.Column("media_type",  sa.String(20),    nullable=False),
        sa.Column("rating",      sa.Integer,       nullable=False),
        sa.Column("review",      sa.Text,          nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "tmdb_id", "media_type", name="uq_user_rating"),
    )

    # --- user_rating_likes ---
    op.create_table(
        "user_rating_likes",
        sa.Column("id",          sa.Integer,       primary_key=True, index=True),
        sa.Column("rating_id",   sa.Integer,       sa.ForeignKey("user_ratings.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id",     sa.Integer,       sa.ForeignKey("users.id",
                  ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("rating_id", "user_id", name="uq_rating_like"),
    )

    # --- release_reminders ---
    op.create_table(
        "release_reminders",
        sa.Column("id",            sa.Integer,       primary_key=True, index=True),
        sa.Column("user_id",       sa.Integer,       sa.ForeignKey("users.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tmdb_id",       sa.Integer,       nullable=False),
        sa.Column("media_type",    sa.String(20),    nullable=False),
        sa.Column("release_date",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("notified",      sa.Boolean,       server_default=sa.text("false"), nullable=False),
        sa.UniqueConstraint("user_id", "tmdb_id", "media_type", name="uq_release_reminder"),
    )

    # --- watch_parties ---
    op.create_table(
        "watch_parties",
        sa.Column("id",               sa.Integer,       primary_key=True, index=True),
        sa.Column("host_user_id",     sa.Integer,       sa.ForeignKey("users.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title",            sa.String(300),   nullable=False),
        sa.Column("tmdb_id",          sa.Integer,       nullable=True),
        sa.Column("media_type",       sa.String(20),    nullable=True),
        sa.Column("scheduled_at",     sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_participants", sa.Integer,       server_default=sa.text("20"), nullable=False),
        sa.Column("chat_room_id",     sa.Integer,       sa.ForeignKey("chat_rooms.id",
                  ondelete="SET NULL"), nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- watch_party_participants ---
    op.create_table(
        "watch_party_participants",
        sa.Column("id",        sa.Integer,       primary_key=True, index=True),
        sa.Column("party_id",  sa.Integer,       sa.ForeignKey("watch_parties.id",
                  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id",   sa.Integer,       sa.ForeignKey("users.id",
                  ondelete="CASCADE"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("party_id", "user_id", name="uq_party_participant"),
    )


def downgrade() -> None:
    op.drop_table("watch_party_participants")
    op.drop_table("watch_parties")
    op.drop_table("release_reminders")
    op.drop_table("user_rating_likes")
    op.drop_table("user_ratings")
    op.drop_table("user_list_items")
    op.drop_table("user_lists")
