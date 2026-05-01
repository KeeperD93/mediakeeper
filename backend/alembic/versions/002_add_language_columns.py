"""add audio_language and subtitle_language to playback_sessions

Revision ID: 002_add_language_columns
Revises: 001_normalize_settings
Create Date: 2026-03-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_add_language_columns"
down_revision: Union[str, None] = "001_normalize_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ajout colonnes langue audio et sous-titres
    op.add_column("playback_sessions", sa.Column("audio_language", sa.String(50), nullable=True))
    op.add_column("playback_sessions", sa.Column("subtitle_language", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("playback_sessions", "subtitle_language")
    op.drop_column("playback_sessions", "audio_language")
