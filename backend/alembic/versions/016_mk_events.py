"""mediakeeper events module — events, invitations, room messages, notifications

Revision ID: 016_mk_events
Revises: 015_chat_reports
Create Date: 2026-04-09
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "016_mk_events"
down_revision: Union[str, None] = "015_chat_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # ---- mk_events ----
    if "mk_events" not in tables:
        op.create_table(
            "mk_events",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "creator_user_id",
                sa.Integer,
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False, server_default="private"),
            # Stored as JSONB on Postgres for fast queries / GIN indexing if needed.
            sa.Column("tmdb_ids", sa.JSON, nullable=False),
            sa.Column(
                "scheduled_at",
                sa.DateTime(timezone=True),
                nullable=False,
                index=True,
            ),
            sa.Column("comment", sa.Text, nullable=True),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="scheduled",
                index=True,
            ),
            sa.Column("room_opened_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )

    # ---- mk_event_invitations ----
    if "mk_event_invitations" not in tables:
        op.create_table(
            "mk_event_invitations",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "event_id",
                sa.Integer,
                sa.ForeignKey("mk_events.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="pending",
            ),
            sa.Column(
                "invite_count",
                sa.Integer,
                nullable=False,
                server_default="1",
            ),
            sa.Column("seat_index", sa.Integer, nullable=True),
            sa.Column(
                "invited_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("event_id", "user_id", name="uq_mk_event_invitation"),
        )

    # ---- mk_event_messages ----
    if "mk_event_messages" not in tables:
        op.create_table(
            "mk_event_messages",
            sa.Column("id", sa.BigInteger, primary_key=True),
            sa.Column(
                "event_id",
                sa.Integer,
                sa.ForeignKey("mk_events.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("content", sa.String(2000), nullable=False),
            sa.Column(
                "sent_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
                index=True,
            ),
        )

    # ---- mk_notifications ----
    if "mk_notifications" not in tables:
        op.create_table(
            "mk_notifications",
            sa.Column("id", sa.BigInteger, primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("type", sa.String(50), nullable=False),
            sa.Column("payload", sa.JSON, nullable=True),
            sa.Column(
                "read",
                sa.Boolean,
                nullable=False,
                server_default=sa.text("false"),
                index=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
                index=True,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "mk_notifications" in tables:
        op.drop_table("mk_notifications")
    if "mk_event_messages" in tables:
        op.drop_table("mk_event_messages")
    if "mk_event_invitations" in tables:
        op.drop_table("mk_event_invitations")
    if "mk_events" in tables:
        op.drop_table("mk_events")
