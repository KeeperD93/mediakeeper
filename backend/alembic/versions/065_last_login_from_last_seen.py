"""Members' last sign-in filled in from their last visit

Only admins had their sign-ins stamped, so the admin "Users" page listed
members who do sign in as never signed in. A profile with no sign-in stamped but
a visit gets that visit as its last sign-in; its address and browser stay empty.
Migration 066 then replaces it with the sign-in the attempts log holds, if any.
Irreversible: the copied dates cannot be told from real sign-ins, so
``downgrade`` is a no-op.

Revision ID: 065_last_login_from_last_seen
Revises: 064_security_cleared_and_automatic
Create Date: 2026-11-01
"""
from alembic import op

revision = "065_last_login_from_last_seen"
down_revision = "064_security_cleared_and_automatic"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE user_profiles SET last_login_at = last_seen_at "
        "WHERE last_login_at IS NULL AND last_seen_at IS NOT NULL"
    )


def downgrade() -> None:
    # Irreversible: the copied dates cannot be told from real sign-ins.
    pass
