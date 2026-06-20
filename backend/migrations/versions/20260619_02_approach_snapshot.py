"""Add immutable external approach-reference snapshots to sessions."""

from alembic import op
import sqlalchemy as sa


revision = "20260619_02"
down_revision = "20260619_01"
branch_labels = None
depends_on = None


APPROACH_COLUMNS = (
    sa.Column("persona_approach_source", sa.String(length=255), nullable=True),
    sa.Column("persona_approach_hash", sa.String(length=64), nullable=True),
    sa.Column("persona_approach_markdown", sa.Text(), nullable=True),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sessions" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("sessions")}
    with op.batch_alter_table("sessions") as batch:
        for column in APPROACH_COLUMNS:
            if column.name not in existing:
                batch.add_column(column)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sessions" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("sessions")}
    with op.batch_alter_table("sessions") as batch:
        for column in reversed(APPROACH_COLUMNS):
            if column.name in existing:
                batch.drop_column(column.name)
