"""Add language-aware longitudinal session memory."""

from alembic import op
import sqlalchemy as sa


revision = "20260620_03"
down_revision = "20260619_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sessions" in inspector.get_table_names():
        existing = {column["name"] for column in inspector.get_columns("sessions")}
        existing_indexes = {index["name"] for index in inspector.get_indexes("sessions")}
        with op.batch_alter_table("sessions") as batch:
            if "continuity_eligible" not in existing:
                batch.add_column(sa.Column("continuity_eligible", sa.Boolean(), nullable=False, server_default=sa.false()))
            if "continuity_snapshot" not in existing:
                batch.add_column(sa.Column("continuity_snapshot", sa.Text(), nullable=False, server_default="{}"))
            if "ix_sessions_continuity_eligible" not in existing_indexes:
                batch.create_index("ix_sessions_continuity_eligible", ["continuity_eligible"], unique=False)
    if "session_summaries" in inspector.get_table_names():
        existing = {column["name"] for column in inspector.get_columns("session_summaries")}
        existing_indexes = {index["name"] for index in inspector.get_indexes("session_summaries")}
        with op.batch_alter_table("session_summaries") as batch:
            if "language" not in existing:
                batch.add_column(sa.Column("language", sa.String(length=10), nullable=True))
            if "structured_data" not in existing:
                batch.add_column(sa.Column("structured_data", sa.Text(), nullable=False, server_default="{}"))
            if "ix_session_summaries_language" not in existing_indexes:
                batch.create_index("ix_session_summaries_language", ["language"], unique=False)
    if "longitudinal_profiles" not in inspector.get_table_names():
        op.create_table(
            "longitudinal_profiles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("language", sa.String(length=10), nullable=False),
            sa.Column("narrative", sa.Text(), nullable=False, server_default=""),
            sa.Column("structured_data", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("eligible_session_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("language", name="uq_longitudinal_profile_language"),
        )
        op.create_index("ix_longitudinal_profiles_language", "longitudinal_profiles", ["language"])
    if "longitudinal_records" not in inspector.get_table_names():
        op.create_table(
            "longitudinal_records",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("record_type", sa.String(length=30), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column("follow_up_question", sa.Text(), nullable=True),
            sa.Column("source_session_id", sa.String(length=64), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_message_ids", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("language", sa.String(length=10), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_longitudinal_records_record_type", "longitudinal_records", ["record_type"])
        op.create_index("ix_longitudinal_records_status", "longitudinal_records", ["status"])
        op.create_index("ix_longitudinal_records_source_session_id", "longitudinal_records", ["source_session_id"])
        op.create_index("ix_longitudinal_records_language", "longitudinal_records", ["language"])


def downgrade() -> None:
    op.drop_table("longitudinal_records")
    op.drop_table("longitudinal_profiles")
    with op.batch_alter_table("session_summaries") as batch:
        batch.drop_index("ix_session_summaries_language")
        batch.drop_column("structured_data")
        batch.drop_column("language")
    with op.batch_alter_table("sessions") as batch:
        batch.drop_index("ix_sessions_continuity_eligible")
        batch.drop_column("continuity_snapshot")
        batch.drop_column("continuity_eligible")
