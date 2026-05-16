"""Drop ``portal_search_documents`` — replaced by live TMDB proxy with cache.

The original local index (migration 038) cached a copy of TMDB
documents to power a fuzzy ``pg_trgm`` search and to flag
``available_on_emby``. It accumulated empty-``poster_url`` rows that
required a separate scheduled enrichment task to backfill, and
maintained stale data once a TMDB poster changed upstream.

The new search service (``services.portal.tmdb_search``) calls
TMDB live with a 5-minute TTL cache and re-stamps
``available_on_emby`` from ``EmbyTmdbIndex`` on every request, so
the local index is no longer needed. This migration drops the
orphan table along with its trigram indexes.

No-op on a fresh install — the table never existed.
"""
from alembic import op
import sqlalchemy as sa

revision = "049_drop_portal_search_documents"
down_revision = "048_mk_event_current_step"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "portal_search_documents" not in inspector.get_table_names():
        return
    # Drop trigram indexes explicitly: Postgres won't auto-drop them
    # when their parent table goes if the extension was disabled at
    # any point between create and drop.
    for idx_name in (
        "ix_portal_search_documents_search_text_trgm",
        "ix_portal_search_documents_title_trgm",
        "ix_portal_search_documents_original_title_trgm",
    ):
        op.execute(f"DROP INDEX IF EXISTS {idx_name}")
    op.drop_table("portal_search_documents")


def downgrade() -> None:
    # No way back — the schema is recreated by migration 038 if you
    # really need to roll back, and the data is unrecoverable since
    # the service no longer populates it.
    raise NotImplementedError(
        "Downgrade past 049 is not supported: the table is repopulated only "
        "by code paths that have been removed."
    )
