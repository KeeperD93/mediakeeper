"""media_requests.available_at + requests.auto_cleanup_days setting.

Adds a dedicated ``available_at`` timestamp on ``media_requests`` so the
auto-cleanup job can window deletions on the exact moment the row
flipped to ``available`` (not the last ``updated_at`` bump, which is
touched on every status change). Existing rows in ``available`` status
are backfilled from ``updated_at`` — best-effort but accurate within a
few days, which is sufficient for a hygiene job.

Also seeds the key/value ``settings`` row ``requests.auto_cleanup_days``
to ``"0"`` (disabled). 0 means the scheduler handler early-returns
without scanning, so the feature stays inert until an admin sets a
positive value.
"""
from alembic import op
import sqlalchemy as sa


revision = "046_request_available_at_and_cleanup_setting"
down_revision = "045_news_scheduling_and_maintenance"
branch_labels = None
depends_on = None


_CLEANUP_SETTING_KEY = "requests.auto_cleanup_days"
_CLEANUP_SETTING_DEFAULT = "0"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    request_cols = {c["name"] for c in inspector.get_columns("media_requests")}
    with op.batch_alter_table("media_requests") as batch_op:
        if "available_at" not in request_cols:
            batch_op.add_column(
                sa.Column("available_at", sa.DateTime(timezone=True), nullable=True)
            )

    bind.execute(
        sa.text(
            "UPDATE media_requests "
            "SET available_at = updated_at "
            "WHERE status = 'available' AND available_at IS NULL"
        )
    )

    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
    )
    existing = bind.execute(
        sa.select(settings.c.key).where(settings.c.key == _CLEANUP_SETTING_KEY)
    ).fetchone()
    if existing is None:
        op.bulk_insert(
            settings,
            [{"key": _CLEANUP_SETTING_KEY, "value": _CLEANUP_SETTING_DEFAULT}],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
    )
    bind.execute(
        sa.delete(settings).where(settings.c.key == _CLEANUP_SETTING_KEY)
    )

    request_cols = {c["name"] for c in inspector.get_columns("media_requests")}
    with op.batch_alter_table("media_requests") as batch_op:
        if "available_at" in request_cols:
            batch_op.drop_column("available_at")
