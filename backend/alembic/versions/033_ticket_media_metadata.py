"""Ticket media metadata: series_emby_id + selected_seasons.

Adds the columns needed to anchor a ticket to a real Emby library item with
season/episode granularity:

- ``series_emby_id`` (str(64), nullable) — Emby Id of the parent series for
  ``media_type`` ∈ {series, season, episode}. Lets the UI render the show's
  poster/backdrop without storing them as URLs.
- ``selected_seasons`` (JSON, nullable) — list of dicts mirroring the
  ``media_requests.requested_seasons`` shape:
  ``[{"season_number": 1, "episodes": [1, 2, 3]}, {"season_number": 2}]``.
  An entry without ``episodes`` means the whole season; an empty list /
  null at the column level means the whole series.

Movies and "other" tickets keep both columns null.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "033_ticket_media_metadata"
down_revision: Union[str, None] = "032_help_articles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("tickets")}

    if "series_emby_id" not in cols:
        op.add_column(
            "tickets",
            sa.Column("series_emby_id", sa.String(64), nullable=True),
        )
    if "selected_seasons" not in cols:
        op.add_column(
            "tickets",
            sa.Column("selected_seasons", sa.JSON, nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("tickets")}

    if "selected_seasons" in cols:
        op.drop_column("tickets", "selected_seasons")
    if "series_emby_id" in cols:
        op.drop_column("tickets", "series_emby_id")
