"""Index users.pending_deletion_at for the periodic GDPR purge scan.

The GDPR purge selects users on ``pending_deletion_at`` (NOT NULL and due),
which was a sequential scan. Add a btree index on that column. ``op.create_index``
runs natively on PostgreSQL and SQLite; the inspector guard keeps the upgrade
idempotent. ``deletion_requested_at`` is intentionally left unindexed — it is
only ever read/written, never used in a query predicate.
"""
from alembic import op
import sqlalchemy as sa


revision = "059_index_pending_deletion_at"
down_revision = "058_security_bool_check_constraints"
branch_labels = None
depends_on = None


_INDEX = "ix_users_pending_deletion_at"


def _index_names(bind) -> set[str]:
    return {ix["name"] for ix in sa.inspect(bind).get_indexes("users")}


def upgrade() -> None:
    bind = op.get_bind()
    if _INDEX not in _index_names(bind):
        op.create_index(_INDEX, "users", ["pending_deletion_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if _INDEX in _index_names(bind):
        op.drop_index(_INDEX, table_name="users")
