"""Add ``tokens_invalidated_at`` on ``users`` for admin-side session revocation.

The portal already revokes sessions through ``user_profiles.tokens_invalidated_at``
(migration 037). Admin sessions live on the ``users`` row and need their own
revocation pivot so a password change on device A can invalidate every JWT
issued before that timestamp on device B.
"""
from alembic import op
import sqlalchemy as sa


revision = "039_users_tokens_invalidated_at"
down_revision = "038_portal_search_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    cols = {c["name"] for c in inspector.get_columns("users")}
    if "tokens_invalidated_at" not in cols:
        op.add_column(
            "users",
            sa.Column("tokens_invalidated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "tokens_invalidated_at" in cols:
        op.drop_column("users", "tokens_invalidated_at")
