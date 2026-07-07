"""feedback_reports table + user_profiles.can_report_feedback

Delegate feedback moderation queue (cycle 3): portal users granted the
``can_report_feedback`` permission file bug/suggestion reports that land here
as ``pending`` for the admin to validate or reject.

Revision ID: 061_feedback_reports
Revises: 060_backfill_anonymous_pseudonyms
Create Date: 2026-07-02
"""
import sqlalchemy as sa
from alembic import op

revision = "061_feedback_reports"
down_revision = "060_backfill_anonymous_pseudonyms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "feedback_reports" not in tables:
        op.create_table(
            "feedback_reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "reporter_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("reporter_name", sa.String(length=100), nullable=True),
            sa.Column("type", sa.String(length=20), server_default="bug", nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("reproduction", sa.Text(), nullable=True),
            sa.Column("zone", sa.String(length=120), nullable=True),
            sa.Column("module", sa.String(length=120), nullable=True),
            sa.Column("tab", sa.String(length=120), nullable=True),
            sa.Column("platform", sa.String(length=20), nullable=True),
            sa.Column("resolution", sa.String(length=40), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("anonymous", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_feedback_reports_reporter_user_id", "feedback_reports", ["reporter_user_id"]
        )
        op.create_index("ix_feedback_reports_status", "feedback_reports", ["status"])
        op.create_index("ix_feedback_reports_rejected_at", "feedback_reports", ["rejected_at"])

    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "can_report_feedback" not in cols:
        op.add_column(
            "user_profiles",
            sa.Column(
                "can_report_feedback",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "can_report_feedback" in cols:
        op.drop_column("user_profiles", "can_report_feedback")
    tables = set(inspector.get_table_names())
    if "feedback_reports" in tables:
        op.drop_table("feedback_reports")
