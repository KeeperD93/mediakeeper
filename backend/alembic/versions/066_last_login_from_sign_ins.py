"""Last sign-in taken from the attempts log where it holds one

``security_attempts`` keeps every successful sign-in with its address and
browser. A profile never really stamped (no address) gets its latest one in place
of the visit copied by 065. The log is keyed by name and outlives an account: only
rows from the profile's lifetime count, so a name reused by a new account does not
inherit the old one's sign-ins. Password changes are logged under their own scope
and are not sign-ins. Irreversible: the replaced dates are gone, so ``downgrade``
is a no-op.

Revision ID: 066_last_login_from_sign_ins
Revises: 065_last_login_from_last_seen
Create Date: 2026-11-01
"""
from alembic import op

revision = "066_last_login_from_sign_ins"
down_revision = "065_last_login_from_last_seen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE user_profiles
        SET last_login_at = latest.created_at,
            last_login_ip = latest.ip,
            last_login_user_agent = substr(latest.user_agent, 1, 255)
        FROM (
            SELECT u.id AS user_id, a.created_at, a.ip, a.user_agent,
                   row_number() OVER (PARTITION BY u.id ORDER BY a.created_at DESC, a.id DESC) AS recency
            FROM security_attempts a
            JOIN users u ON lower(a.username) = lower(u.username)
            WHERE a.success = 1 AND a.scope IN ('portal', 'admin')
        ) latest
        WHERE latest.user_id = user_profiles.user_id
          AND latest.recency = 1
          AND user_profiles.last_login_ip IS NULL
          AND latest.created_at >= user_profiles.created_at
    """)


def downgrade() -> None:
    # Irreversible: the replaced dates are gone.
    pass
