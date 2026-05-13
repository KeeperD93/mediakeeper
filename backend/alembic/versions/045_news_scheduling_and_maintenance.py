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

DDL pattern: native ``ADD/DROP COLUMN IF [NOT] EXISTS`` on Postgres
(``op.batch_alter_table`` was a silent no-op on asyncpg in some
deployments — alembic_version stamped, ALTER never applied). SQLite
falls back to the inspector-guarded ``add_column`` / ``drop_column``
pair. A post-condition raises if the expected columns are still
missing.
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

_NEWS_COLUMNS = ("start_at", "end_at")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        for col in _NEWS_COLUMNS:
            op.execute(
                f'ALTER TABLE "news" '
                f'ADD COLUMN IF NOT EXISTS "{col}" TIMESTAMP WITH TIME ZONE'
            )
    else:
        inspector = sa.inspect(bind)
        news_cols = {c["name"] for c in inspector.get_columns("news")}
        for col in _NEWS_COLUMNS:
            if col not in news_cols:
                op.add_column(
                    "news",
                    sa.Column(col, sa.DateTime(timezone=True), nullable=True),
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

    news_cols_after = {
        c["name"] for c in sa.inspect(bind).get_columns("news")
    }
    missing = [c for c in _NEWS_COLUMNS if c not in news_cols_after]
    if missing:
        raise RuntimeError(
            f"Migration 045 ran but news columns are still missing: {missing}. "
            "Underlying DDL did not apply."
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
    )
    bind.execute(
        sa.delete(settings).where(settings.c.key.like("maintenance.%"))
    )

    if dialect == "postgresql":
        for col in reversed(_NEWS_COLUMNS):
            op.execute(
                f'ALTER TABLE "news" DROP COLUMN IF EXISTS "{col}"'
            )
    else:
        inspector = sa.inspect(bind)
        news_cols = {c["name"] for c in inspector.get_columns("news")}
        for col in reversed(_NEWS_COLUMNS):
            if col in news_cols:
                op.drop_column("news", col)
