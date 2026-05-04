"""Login history table + ``tokens_invalidated_at`` on user_profiles.

- ``user_login_history`` records every successful + failed Portal login
  (one row per attempt). Powers the Security tab list.
- ``tokens_invalidated_at`` on ``user_profiles`` flags an account whose
  active sessions should be rejected. The Portal cookie path checks the
  token ``iat`` against this column on every request.
"""
from alembic import op
import sqlalchemy as sa


revision = "037_login_history_logout"
down_revision = "036_user_profile_emby_disabled"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "tokens_invalidated_at" not in cols:
        op.add_column(
            "user_profiles",
            sa.Column("tokens_invalidated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "user_login_history" not in inspector.get_table_names():
        op.create_table(
            "user_login_history",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=True, index=True),
            sa.Column("username", sa.String(100), nullable=True),
            sa.Column("source", sa.String(20), nullable=False),
            sa.Column("success", sa.Boolean(), nullable=False),
            sa.Column("ip", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.String(255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_user_login_history_user_created",
            "user_login_history",
            ["user_id", "created_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "user_login_history" in inspector.get_table_names():
        try:
            op.drop_index("ix_user_login_history_user_created", table_name="user_login_history")
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass
        op.drop_table("user_login_history")
    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "tokens_invalidated_at" in cols:
        op.drop_column("user_profiles", "tokens_invalidated_at")
