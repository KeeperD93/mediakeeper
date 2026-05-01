"""Security log tables: login attempts + blocks."""
from alembic import op
import sqlalchemy as sa

revision = "025_security_log"
down_revision = "024_xp_boost_events"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "security_attempts" not in tables:
        op.create_table(
            "security_attempts",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("ip", sa.String(64), nullable=False, index=True),
            sa.Column("username", sa.String(100), nullable=True, index=True),
            sa.Column("scope", sa.String(20), nullable=False),
            sa.Column("success", sa.Integer, nullable=False, server_default="0"),
            sa.Column("user_agent", sa.String(300), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
                index=True,
            ),
        )
        op.create_index(
            "ix_security_attempts_ip_created",
            "security_attempts",
            ["ip", "created_at"],
        )
        op.create_index(
            "ix_security_attempts_user_created",
            "security_attempts",
            ["username", "created_at"],
        )

    if "security_blocks" not in tables:
        op.create_table(
            "security_blocks",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("ip", sa.String(64), nullable=True, index=True),
            sa.Column("username", sa.String(100), nullable=True, index=True),
            sa.Column("scope", sa.String(20), nullable=False),
            sa.Column("permanent", sa.Integer, nullable=False, server_default="0"),
            sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reason", sa.String(200), nullable=True),
            sa.Column(
                "created_by",
                sa.Integer,
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "security_blocks" in tables:
        op.drop_table("security_blocks")
    if "security_attempts" in tables:
        op.drop_table("security_attempts")
