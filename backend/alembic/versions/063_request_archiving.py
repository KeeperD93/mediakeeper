"""Archive served requests instead of deleting them

The automatic cleanup now archives ``available`` requests (hidden from the
Requests lists, still counted by totals, statistics and trophies) instead of
deleting them, hence ``media_requests.archived_at``. Requests marked available
by hand never got an ``available_at`` date, so the job skipped them forever:
they get one now from their last update, always later than the real date, so
nothing is archived early. Downgrade drops the column and keeps those dates.

Revision ID: 063_request_archiving
Revises: 062_continuous_watch_measurement
Create Date: 2026-10-15
"""
import sqlalchemy as sa
from alembic import op

revision = "063_request_archiving"
down_revision = "062_continuous_watch_measurement"
branch_labels = None
depends_on = None

_TABLE = "media_requests"
_INDEX = "ix_media_requests_archived_at"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "archived_at" not in {c["name"] for c in inspector.get_columns(_TABLE)}:
        op.add_column(_TABLE, sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    if _INDEX not in {i["name"] for i in inspector.get_indexes(_TABLE)}:
        op.create_index(_INDEX, _TABLE, ["archived_at"])
    op.execute(
        "UPDATE media_requests "
        "SET available_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) "
        "WHERE status = 'available' AND available_at IS NULL"
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _INDEX in {i["name"] for i in inspector.get_indexes(_TABLE)}:
        op.drop_index(_INDEX, table_name=_TABLE)
    if "archived_at" in {c["name"] for c in inspector.get_columns(_TABLE)}:
        op.drop_column(_TABLE, "archived_at")
