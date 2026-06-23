"""Add CHECK(0/1) guards on the security boolean-as-integer columns.

``SecurityAttempt.success`` and ``SecurityBlock.permanent`` store a boolean as
an integer (0/1) for cross-backend portability. These DB-level guards stop a
raw-SQL / ORM-bypass write of any other value from corrupting the rate-limit
counts. Applied on PostgreSQL only — SQLite test/dev DBs build the schema from
the model via ``create_all`` and already carry the constraints; the inspector
guard keeps the upgrade idempotent.
"""
from alembic import op
import sqlalchemy as sa


revision = "058_security_bool_check_constraints"
down_revision = "057_request_quota_auto_mode"
branch_labels = None
depends_on = None


_CONSTRAINTS = (
    ("security_attempts", "ck_security_attempts_success_bool", "success IN (0, 1)"),
    ("security_blocks", "ck_security_blocks_permanent_bool", "permanent IN (0, 1)"),
)


def _check_names(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_check_constraints(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, name, condition in _CONSTRAINTS:
        if name not in _check_names(bind, table):
            op.create_check_constraint(name, table, condition)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, name, _condition in _CONSTRAINTS:
        if name in _check_names(bind, table):
            op.drop_constraint(name, table, type_="check")
