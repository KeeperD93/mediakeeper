"""Add ``force_run_requested_at`` to ``scheduler_tasks``.

Bridges the API web process and the background worker process when
``MK_SEPARATE_BACKGROUND_WORKER=true``. The API can't call the
scheduler instance directly (each process has its own
``_scheduler_instance`` global, ``None`` on the web side), so it
stamps a timestamp on the row instead. The scheduler's main loop —
which already runs in the worker process — polls this column every
tick and triggers ``_run_task`` for any row whose flag is set, then
clears it.

DDL pattern mirrors migration 048: native ``ADD COLUMN IF NOT
EXISTS`` on Postgres so a half-applied migration on a hot deploy
heals on the next boot, and an inspector-guarded ``add_column`` on
SQLite for the test harness.
"""
from alembic import op
import sqlalchemy as sa


revision = "050_scheduler_force_run"
down_revision = "049_drop_portal_search_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute(
            "ALTER TABLE scheduler_tasks "
            "ADD COLUMN IF NOT EXISTS force_run_requested_at "
            "TIMESTAMP WITH TIME ZONE"
        )
        return
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("scheduler_tasks")}
    if "force_run_requested_at" in cols:
        return
    with op.batch_alter_table("scheduler_tasks") as batch:
        batch.add_column(
            sa.Column(
                "force_run_requested_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute(
            "ALTER TABLE scheduler_tasks DROP COLUMN IF EXISTS force_run_requested_at"
        )
        return
    with op.batch_alter_table("scheduler_tasks") as batch:
        batch.drop_column("force_run_requested_at")
