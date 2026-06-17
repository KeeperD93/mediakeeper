"""Request quota: auto-mode bounds + manual/auto vocabulary.

Adds ``auto_min`` / ``auto_max`` (per-user clamps for the engagement-scored
'auto' mode) and ``last_recomputed_at`` to ``request_quotas``, and renames the
legacy ``mode`` values ``fixed`` -> ``manual`` and ``proportional`` -> ``auto``
to match the product vocabulary. ``op.add_column`` runs natively on both
PostgreSQL and SQLite and the inspector guard keeps the upgrade idempotent. The
``mode`` server-default flip is applied on PostgreSQL only — SQLite test DBs
build the schema from the model via ``create_all`` and already carry the new
default.
"""
from alembic import op
import sqlalchemy as sa


revision = "057_request_quota_auto_mode"
down_revision = "056_user_preferences_table_columns"
branch_labels = None
depends_on = None


def _cols(bind) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns("request_quotas")}


def upgrade() -> None:
    bind = op.get_bind()
    cols = _cols(bind)
    if "auto_min" not in cols:
        op.add_column(
            "request_quotas",
            sa.Column("auto_min", sa.Integer(), nullable=False, server_default="2"),
        )
    if "auto_max" not in cols:
        op.add_column(
            "request_quotas",
            sa.Column("auto_max", sa.Integer(), nullable=False, server_default="15"),
        )
    if "last_recomputed_at" not in cols:
        op.add_column(
            "request_quotas",
            sa.Column("last_recomputed_at", sa.DateTime(timezone=True), nullable=True),
        )
    # Rename the mode vocabulary to match the product (manual / auto).
    op.execute(sa.text("UPDATE request_quotas SET mode = 'manual' WHERE mode = 'fixed'"))
    op.execute(sa.text("UPDATE request_quotas SET mode = 'auto' WHERE mode = 'proportional'"))
    # New rows default to 'manual'. SQLite rebuilds from the model via
    # create_all and already has it; only PostgreSQL needs the live flip.
    if bind.dialect.name != "sqlite":
        op.alter_column("request_quotas", "mode", server_default="manual")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column("request_quotas", "mode", server_default="fixed")
    op.execute(sa.text("UPDATE request_quotas SET mode = 'fixed' WHERE mode = 'manual'"))
    op.execute(sa.text("UPDATE request_quotas SET mode = 'proportional' WHERE mode = 'auto'"))
    cols = _cols(bind)
    with op.batch_alter_table("request_quotas") as batch:
        if "last_recomputed_at" in cols:
            batch.drop_column("last_recomputed_at")
        if "auto_max" in cols:
            batch.drop_column("auto_max")
        if "auto_min" in cols:
            batch.drop_column("auto_min")
