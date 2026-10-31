"""Neutralised sign-in failures and automatic blocks marked as such

``security_attempts.cleared_at`` is set when an unblock or a later successful
sign-in stops a failure from counting: it stays listed, no counter counts it.
``security_blocks.automatic`` tells the blocks set after repeated failures from
an admin's own: ``created_by`` alone cannot, since it becomes NULL when the admin
is deleted. Existing rows get the marker from their reason, which only automatic
blocks carry. Downgrade drops both columns: failures neutralised in the last few
minutes count again until they leave the window.

Revision ID: 064_security_cleared_and_automatic
Revises: 063_request_archiving
Create Date: 2026-10-25
"""
import sqlalchemy as sa
from alembic import op

revision = "064_security_cleared_and_automatic"
down_revision = "063_request_archiving"
branch_labels = None
depends_on = None

_ATTEMPTS = "security_attempts"
_BLOCKS = "security_blocks"
_CHECK = "ck_security_blocks_automatic_bool"


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if "cleared_at" not in _columns(_ATTEMPTS):
        op.add_column(_ATTEMPTS, sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True))
    if "automatic" not in _columns(_BLOCKS):
        op.add_column(
            _BLOCKS,
            sa.Column("automatic", sa.Integer(), nullable=False, server_default="0"),
        )
    # SQLite test databases are built from the model, which carries the check.
    if bind.dialect.name == "postgresql":
        checks = {c["name"] for c in sa.inspect(bind).get_check_constraints(_BLOCKS)}
        if _CHECK not in checks:
            op.create_check_constraint(_CHECK, _BLOCKS, "automatic IN (0, 1)")
    op.execute(
        "UPDATE security_blocks SET automatic = 1 "
        "WHERE created_by IS NULL AND permanent = 0 "
        "AND reason LIKE 'auto\\_block\\_bruteforce\\_%' ESCAPE '\\'"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        checks = {c["name"] for c in sa.inspect(bind).get_check_constraints(_BLOCKS)}
        if _CHECK in checks:
            op.drop_constraint(_CHECK, _BLOCKS, type_="check")
    if "automatic" in _columns(_BLOCKS):
        op.drop_column(_BLOCKS, "automatic")
    if "cleared_at" in _columns(_ATTEMPTS):
        op.drop_column(_ATTEMPTS, "cleared_at")
