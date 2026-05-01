"""Help center: articles + translations tables (multilingual help center).

Two tables:
- ``help_articles`` — language-agnostic metadata (slug, category, icon,
  ordering, draft + soft-delete flags).
- ``help_article_translations`` — one row per (article, lang) with the
  rendered HTML body. UNIQUE(article_id, lang).

Seed of the 15 starter articles is performed at app boot via
``services.portal.help.ensure_seed`` (idempotent on slug). Keeping the
HTML out of the migration keeps it readable and lets us evolve copy
without spawning new revisions.
"""
from alembic import op
import sqlalchemy as sa


revision = "032_help_articles"
down_revision = "031_profile_settings_premium"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "help_articles" not in existing:
        op.create_table(
            "help_articles",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("slug", sa.String(160), nullable=False),
            sa.Column("category", sa.String(40), nullable=False),
            sa.Column("icon", sa.String(60), nullable=True),
            sa.Column("sort_order", sa.Integer, nullable=False,
                      server_default="0"),
            sa.Column("is_draft", sa.Boolean, nullable=False,
                      server_default=sa.text("false")),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_help_articles_slug", "help_articles", ["slug"],
                        unique=True)
        op.create_index("ix_help_articles_category", "help_articles",
                        ["category"])
        op.create_index("ix_help_articles_sort_order", "help_articles",
                        ["sort_order"])
        op.create_index("ix_help_articles_deleted_at", "help_articles",
                        ["deleted_at"])

    if "help_article_translations" not in existing:
        op.create_table(
            "help_article_translations",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("article_id", sa.Integer,
                      sa.ForeignKey("help_articles.id", ondelete="CASCADE"),
                      nullable=False),
            sa.Column("lang", sa.String(8), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("body_html", sa.Text, nullable=False,
                      server_default=""),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("article_id", "lang",
                                name="uq_help_article_lang"),
        )
        op.create_index("ix_help_article_translations_article_id",
                        "help_article_translations", ["article_id"])
        op.create_index("ix_help_article_translations_lang",
                        "help_article_translations", ["lang"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "help_article_translations" in existing:
        op.drop_index("ix_help_article_translations_lang",
                      table_name="help_article_translations")
        op.drop_index("ix_help_article_translations_article_id",
                      table_name="help_article_translations")
        op.drop_table("help_article_translations")

    if "help_articles" in existing:
        op.drop_index("ix_help_articles_deleted_at", table_name="help_articles")
        op.drop_index("ix_help_articles_sort_order", table_name="help_articles")
        op.drop_index("ix_help_articles_category", table_name="help_articles")
        op.drop_index("ix_help_articles_slug", table_name="help_articles")
        op.drop_table("help_articles")
