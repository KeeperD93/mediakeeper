"""Portal search index backed by PostgreSQL trigram search."""
from alembic import op
import sqlalchemy as sa


revision = "038_portal_search_documents"
down_revision = "037_login_history_logout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    if "portal_search_documents" not in inspector.get_table_names():
        op.create_table(
            "portal_search_documents",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tmdb_id", sa.Integer(), nullable=False),
            sa.Column("media_type", sa.String(20), nullable=False),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("original_title", sa.String(500), nullable=True),
            sa.Column("search_text", sa.Text(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=True),
            sa.Column("overview", sa.Text(), nullable=True),
            sa.Column("poster_url", sa.String(700), nullable=True),
            sa.Column("backdrop_url", sa.String(700), nullable=True),
            sa.Column("vote_average", sa.Float(), nullable=False, server_default="0"),
            sa.Column("popularity", sa.Float(), nullable=False, server_default="0"),
            sa.Column("genres", sa.Text(), nullable=True),
            sa.Column(
                "available_on_emby",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("source", sa.String(32), nullable=False, server_default="tmdb"),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint("tmdb_id", "media_type", name="uq_portal_search_tmdb_media"),
        )
        op.create_index("ix_portal_search_documents_tmdb_id", "portal_search_documents", ["tmdb_id"])
        op.create_index(
            "ix_portal_search_documents_media_type",
            "portal_search_documents",
            ["media_type"],
        )
        op.create_index("ix_portal_search_documents_year", "portal_search_documents", ["year"])
        op.create_index(
            "ix_portal_search_documents_available_on_emby",
            "portal_search_documents",
            ["available_on_emby"],
        )

    if dialect == "postgresql":
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_portal_search_documents_search_text_trgm
            ON portal_search_documents
            USING gin (search_text gin_trgm_ops)
            """
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_portal_search_documents_title_trgm
            ON portal_search_documents
            USING gin (title gin_trgm_ops)
            """
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_portal_search_documents_original_title_trgm
            ON portal_search_documents
            USING gin (original_title gin_trgm_ops)
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "portal_search_documents" in inspector.get_table_names():
        op.drop_table("portal_search_documents")
