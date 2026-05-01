"""Chat unread persistence: chat_last_read_message_id on user_profiles.

Stores the id of the latest chat message a user has read, so the unread
counter on the FAB badge survives reconnections / page reloads. NULL means
the user has never opened the chat (counter = total messages in the room).

Single global lounge for now → one column on the profile is enough; if we
ever ship multi-room with per-user state, we'll move to a dedicated
``chat_reads(user_id, room_id, last_message_id)`` table.
"""
from alembic import op
import sqlalchemy as sa


revision = "034_chat_last_read"
down_revision = "033_ticket_media_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_profiles")}

    if "chat_last_read_message_id" not in cols:
        op.add_column(
            "user_profiles",
            sa.Column("chat_last_read_message_id", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_profiles")}

    if "chat_last_read_message_id" in cols:
        op.drop_column("user_profiles", "chat_last_read_message_id")
