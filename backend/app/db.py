from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TherapySession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    language: Mapped[str] = mapped_column(String(10))
    psychologist_name: Mapped[str] = mapped_column(String(100))
    selected_approaches: Mapped[str] = mapped_column(Text)
    persona_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    persona_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    persona_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    persona_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    persona_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_approach_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    persona_approach_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    persona_approach_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_voice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    persona_voice_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    continuity_eligible: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    continuity_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="active")
    messages: Mapped[list["Message"]] = relationship(cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    audio_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    structured_data: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    embedded: Mapped[bool] = mapped_column(Boolean, default=False)
    vector_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


class LongitudinalProfile(Base):
    __tablename__ = "longitudinal_profiles"
    __table_args__ = (UniqueConstraint("language", name="uq_longitudinal_profile_language"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    language: Mapped[str] = mapped_column(String(10), index=True)
    narrative: Mapped[str] = mapped_column(Text, default="")
    structured_data: Mapped[str] = mapped_column(Text, default="{}")
    eligible_session_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class LongitudinalRecord(Base):
    __tablename__ = "longitudinal_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    record_type: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    follow_up_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    source_message_ids: Mapped[str] = mapped_column(Text, default="[]")
    language: Mapped[str] = mapped_column(String(10), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    memory_type: Mapped[str] = mapped_column(String(50), index=True)
    content: Mapped[str] = mapped_column(Text)
    source_session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    source_message_ids: Mapped[str] = mapped_column(Text, default="[]")
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    language: Mapped[str] = mapped_column(String(10))
    embedded: Mapped[bool] = mapped_column(Boolean, default=False)
    vector_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


class AudioLog(Base):
    __tablename__ = "audio_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    file_path: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    delete_after_processing: Mapped[bool] = mapped_column(Boolean, default=True)


class Database:
    def __init__(self, url: str):
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, connect_args=connect_args)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def session(self) -> Iterator[Session]:
        with self.session_factory() as database_session:
            yield database_session
