"""Add immutable persona snapshots to sessions."""

from alembic import op
import sqlalchemy as sa

revision = "20260619_01"
down_revision = None
branch_labels = None
depends_on = None

PERSONA_COLUMNS = (
    sa.Column("persona_id", sa.String(length=64), nullable=True),
    sa.Column("persona_version", sa.Integer(), nullable=True),
    sa.Column("persona_hash", sa.String(length=64), nullable=True),
    sa.Column("persona_role", sa.String(length=100), nullable=True),
    sa.Column("persona_markdown", sa.Text(), nullable=True),
    sa.Column("persona_voice_id", sa.String(length=128), nullable=True),
    sa.Column("persona_voice_model", sa.String(length=100), nullable=True),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sessions" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("sessions")}
    with op.batch_alter_table("sessions") as batch:
        for column in PERSONA_COLUMNS:
            if column.name not in existing:
                batch.add_column(column)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sessions" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("sessions")}
    with op.batch_alter_table("sessions") as batch:
        for column in reversed(PERSONA_COLUMNS):
            if column.name in existing:
                batch.drop_column(column.name)
