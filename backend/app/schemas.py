from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    retryable: bool = False


class SessionStartRequest(BaseModel):
    language: str | None = None


class PersonaResponse(BaseModel):
    id: str
    display_name: str
    version: int
    language: str
    role: str
    approaches: list[str]
    image_url: str


class SessionStartResponse(BaseModel):
    session_id: str
    language: str
    psychologist_name: str
    selected_approaches: list[str]
    persona_id: str
    persona_version: int
    persona_hash: str
    disclaimer: str | None
    vad: dict[str, int]


class VoiceTurnResponse(BaseModel):
    session_id: str
    user_text: str
    assistant_text: str
    audio_url: str | None
    warning: str | None = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class MessagesResponse(BaseModel):
    session_id: str
    messages: list[MessageResponse]


class MemoryItemResponse(BaseModel):
    memory_id: str
    memory_type: str
    content: str
    importance: float


class SessionEndResponse(BaseModel):
    session_id: str
    status: str
    summary: str | None = None
    memories: list[MemoryItemResponse] = []


class SummaryResponse(BaseModel):
    session_id: str
    summary: str
    memories: list[MemoryItemResponse]


class HealthResponse(BaseModel):
    status: str
    providers_ready: bool
    database: str
    vector_memory: str
    persona: str
