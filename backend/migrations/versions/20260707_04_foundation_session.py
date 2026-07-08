"""Track foundation sessions used as the continuity baseline."""

from alembic import op
import sqlalchemy as sa


revision = "20260707_04"
down_revision = "20260620_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sessions" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("sessions")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("sessions")}
    with op.batch_alter_table("sessions") as batch:
        if "is_foundation_session" not in existing:
            batch.add_column(sa.Column("is_foundation_session", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "ix_sessions_is_foundation_session" not in existing_indexes:
            batch.create_index("ix_sessions_is_foundation_session", ["is_foundation_session"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sessions" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("sessions")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("sessions")}
    with op.batch_alter_table("sessions") as batch:
        if "ix_sessions_is_foundation_session" in existing_indexes:
            batch.drop_index("ix_sessions_is_foundation_session")
        if "is_foundation_session" in existing:
            batch.drop_column("is_foundation_session")
