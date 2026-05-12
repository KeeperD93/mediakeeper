"""News scheduling columns + maintenance-mode settings.

Two unrelated portal features land in the same revision:

* ``news.start_at`` / ``news.end_at`` (both ``DateTime(timezone=True)``,
  nullable) — let admins publish announcements ahead of time or expire
  them on a date. NULL ``start_at`` means "live immediately", NULL
  ``end_at`` means "never expires". The user-facing list endpoint
  filters scheduled/expired rows; the admin list keeps them all.

* Three ``maintenance.*`` rows in the existing key/value ``settings``
  table seeded with FR/EN defaults. When ``maintenance.enabled`` flips
  to ``true``, the portal router guard redirects non-admins to a
  dedicated holding page reading those texts.

The downgrade drops the columns and deletes the three settings rows.
"""
from alembic import op
import sqlalchemy as sa


revision = "045_news_scheduling_and_maintenance"
down_revision = "044_playback_pause_events"
branch_labels = None
depends_on = None


_MAINTENANCE_SETTINGS = (
    ("maintenance.enabled", "false"),
    (
        "maintenance.text_fr",
        "Le site est actuellement en maintenance, "
        "merci de votre compréhension.",
    ),
    (
        "maintenance.text_en",
        "The site is currently under maintenance, "
        "thanks for your understanding.",
    ),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    news_cols = {c["name"] for c in inspector.get_columns("news")}
    with op.batch_alter_table("news") as batch_op:
        if "start_at" not in news_cols:
            batch_op.add_column(
                sa.Column("start_at", sa.DateTime(timezone=True), nullable=True)
            )
        if "end_at" not in news_cols:
            batch_op.add_column(
                sa.Column("end_at", sa.DateTime(timezone=True), nullable=True)
            )

    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
    )
    existing = {
        row[0]
        for row in bind.execute(
            sa.select(settings.c.key).where(settings.c.key.like("maintenance.%"))
        ).fetchall()
    }
    rows = [
        {"key": k, "value": v}
        for k, v in _MAINTENANCE_SETTINGS
        if k not in existing
    ]
    if rows:
        op.bulk_insert(settings, rows)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
    )
    bind.execute(
        sa.delete(settings).where(settings.c.key.like("maintenance.%"))
    )

    news_cols = {c["name"] for c in inspector.get_columns("news")}
    with op.batch_alter_table("news") as batch_op:
        if "end_at" in news_cols:
            batch_op.drop_column("end_at")
        if "start_at" in news_cols:
            batch_op.drop_column("start_at")
