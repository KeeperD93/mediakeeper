"""Add avatar_effect column to user_profiles (master avatar cosmetic)."""
from alembic import op
import sqlalchemy as sa

revision = "022_profile_avatar_effect"
down_revision = "021_user_ach_unique_idx"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "avatar_effect" not in cols:
        op.add_column(
            "user_profiles",
            sa.Column("avatar_effect", sa.String(50), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "avatar_effect" in cols:
        op.drop_column("user_profiles", "avatar_effect")
