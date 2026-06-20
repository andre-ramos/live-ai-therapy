from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .config import PROJECT_ROOT, load_app_config, load_runtime_settings
from .db import AudioLog, Database, LongitudinalRecord, Memory, Message, SessionSummary, TherapySession
from .memory import VectorMemory
from .persona import PersonaLanguageMismatchError, PersonaLoader, PersonaUnavailableError
from .providers import ElevenLabsProvider, OpenAIProviders, UnconfiguredProvider
from .schemas import (
    HealthResponse,
    MemoryItemResponse,
    MessageResponse,
    MessagesResponse,
    PersonaResponse,
    SessionEndResponse,
    SessionStartRequest,
    SessionStartResponse,
    SummaryResponse,
    VoiceTurnResponse,
)
from .services import TherapyService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
config = load_app_config()
settings = load_runtime_settings()
database = Database(settings.database_url)
persona_loader = PersonaLoader(config, settings)

if settings.openai_api_key:
    openai_provider = OpenAIProviders(
        settings.openai_api_key,
        config.stt.model,
        config.llm.model,
        config.embeddings.model,
    )
else:
    openai_provider = UnconfiguredProvider()

tts_provider = (
    ElevenLabsProvider(settings.elevenlabs_api_key)
    if settings.elevenlabs_api_key
    else UnconfiguredProvider()
)
vector_memory = VectorMemory(settings.vector_db_path, openai_provider)
therapy = TherapyService(
    config, settings, openai_provider, openai_provider, tts_provider, vector_memory, persona_loader
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.audio_tmp_path).mkdir(parents=True, exist_ok=True)
    database.create_all()
    try:
        vector_memory.initialize()
    except Exception as error:
        logger.warning("Vector memory startup failed: %s", type(error).__name__)
    with database.session_factory() as db:
        therapy.cleanup_expired_audio(db)
    yield


app = FastAPI(title="Live Therapy", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def frontend_cache_policy(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path == "/styles.css" or request.url.path.startswith("/src/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def get_db():
    yield from database.session()


DbSession = Annotated[Session, Depends(get_db)]


def api_error(status: int, code: str, message: str, retryable: bool = False) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message, "retryable": retryable})


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exception: HTTPException):
    if isinstance(exception.detail, dict) and {"code", "message", "retryable"} <= exception.detail.keys():
        return JSONResponse(status_code=exception.status_code, content=exception.detail)
    return JSONResponse(
        status_code=exception.status_code,
        content={"code": "http_error", "message": str(exception.detail), "retryable": False},
    )


@app.get("/api/health", response_model=HealthResponse)
def health(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ready"
    except Exception:
        db_status = "unavailable"
    try:
        persona_loader.load()
        persona_status = "ready"
    except PersonaUnavailableError:
        persona_status = "unavailable"
    return HealthResponse(
        status="ready" if db_status == "ready" and persona_status == "ready" else "degraded",
        providers_ready=settings.providers_ready,
        database=db_status,
        vector_memory="ready" if vector_memory.ready else "degraded",
        persona=persona_status,
    )


@app.get("/api/persona", response_model=PersonaResponse)
def get_persona():
    try:
        persona = persona_loader.load()
    except PersonaUnavailableError as error:
        raise api_error(503, "persona_unavailable", str(error), True) from error
    return PersonaResponse(
        id=persona.id,
        display_name=persona.display_name,
        version=persona.version,
        language=persona.language,
        role=persona.role,
        approaches=persona.approaches,
        image_url=f"/api/persona/image?v={persona.image_hash}",
    )


@app.get("/api/persona/image", include_in_schema=False)
def get_persona_image():
    try:
        persona = persona_loader.load()
    except PersonaUnavailableError as error:
        raise api_error(503, "persona_unavailable", str(error), True) from error
    return FileResponse(
        persona.image_path,
        media_type=persona.image_media_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.get("/assets/sandy.jpg", include_in_schema=False)
def legacy_persona_image():
    """Keep older cached frontend bundles pointed at the configured persona portrait."""
    return get_persona_image()


@app.post("/api/session/start", response_model=SessionStartResponse, status_code=201)
def start_session(payload: SessionStartRequest, db: DbSession):
    try:
        record = therapy.start_session(db, payload.language)
    except PersonaLanguageMismatchError as error:
        raise api_error(422, "persona_language_mismatch", str(error)) from error
    except PersonaUnavailableError as error:
        raise api_error(503, "persona_language_unavailable", str(error), True) from error
    disclaimer = {
        "pt-BR": "Sandy é uma assistente virtual de apoio psicológico e não substitui atendimento profissional ou de emergência.",
        "en-US": "Sandy is a virtual psychological support assistant and does not replace professional or emergency care.",
    }.get(record.language)
    return SessionStartResponse(
        session_id=record.id,
        language=record.language,
        psychologist_name=record.psychologist_name,
        selected_approaches=json.loads(record.selected_approaches),
        persona_id=record.persona_id,
        persona_version=record.persona_version,
        persona_hash=record.persona_hash,
        disclaimer=disclaimer,
        vad={
            "minimum_recording_ms": config.vad.minimum_recording_ms,
            "silence_duration_ms": config.vad.silence_duration_ms,
            "maximum_recording_ms": config.vad.maximum_recording_ms,
            "post_playback_delay_ms": config.vad.post_playback_delay_ms,
        },
    )


@app.post("/api/voice-turn", response_model=VoiceTurnResponse)
def voice_turn(
    db: DbSession,
    session_id: Annotated[str, Form()],
    audio: Annotated[UploadFile, File()],
    client_timestamp: Annotated[str | None, Form()] = None,
    language_override: Annotated[str | None, Form()] = None,
):
    del client_timestamp
    if not settings.openai_api_key:
        raise api_error(503, "provider_not_configured", "OpenAI is not configured on the server.", True)
    suffix_by_type = {
        "audio/webm": ".webm",
        "audio/mp4": ".m4a",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
    }
    content_type = (audio.content_type or "audio/webm").split(";", 1)[0]
    suffix = suffix_by_type.get(content_type, ".webm")
    try:
        record = db.get(TherapySession, session_id)
        if language_override and record and language_override != record.language:
            raise PersonaLanguageMismatchError("A voice turn cannot override the session language.")
        result = therapy.process_voice_turn(db, session_id, audio.file.read(), suffix)
    except PersonaLanguageMismatchError as error:
        raise api_error(422, "persona_language_mismatch", str(error)) from error
    except LookupError as error:
        raise api_error(404, "session_not_found", str(error)) from error
    except ValueError as error:
        raise api_error(422, "audio_not_understood", str(error), True) from error
    except Exception as error:
        logger.exception("Voice turn failed")
        raise api_error(502, "voice_turn_failed", "Não foi possível processar sua fala. Tente novamente.", True) from error
    return VoiceTurnResponse(
        session_id=session_id,
        user_text=result.user_text,
        assistant_text=result.assistant_text,
        audio_url=f"/api/audio/{result.audio_id}" if result.audio_id else None,
        warning=result.warning,
    )


@app.get("/api/audio/{audio_id}")
def get_audio(audio_id: str, db: DbSession):
    record = db.get(AudioLog, audio_id)
    if not record or not Path(record.file_path).is_file():
        raise api_error(404, "audio_not_found", "Audio not found or expired.")
    return FileResponse(record.file_path, media_type="audio/mpeg", filename=f"{audio_id}.mp3")


@app.get("/api/session/{session_id}/messages", response_model=MessagesResponse)
def get_messages(session_id: str, db: DbSession):
    if not db.get(TherapySession, session_id):
        raise api_error(404, "session_not_found", "Session not found.")
    rows = db.scalars(select(Message).where(Message.session_id == session_id).order_by(Message.created_at)).all()
    return MessagesResponse(
        session_id=session_id,
        messages=[MessageResponse(id=row.id, role=row.role, content=row.content, created_at=row.created_at) for row in rows],
    )


def memory_responses(rows: list[Memory]) -> list[MemoryItemResponse]:
    return [
        MemoryItemResponse(
            memory_id=row.id,
            memory_type=row.memory_type,
            content=row.content,
            importance=row.importance,
        )
        for row in rows
    ]


@app.post("/api/session/{session_id}/end", response_model=SessionEndResponse)
def end_session(session_id: str, db: DbSession):
    try:
        summary, memories = therapy.end_session(db, session_id)
    except LookupError as error:
        raise api_error(404, "session_not_found", str(error)) from error
    except Exception as error:
        logger.exception("Session summarization failed")
        record = db.get(TherapySession, session_id)
        if record:
            record.status = "ended"
            db.commit()
        return SessionEndResponse(session_id=session_id, status="ended", summary=None, memories=[])
    return SessionEndResponse(
        session_id=session_id, status="ended", summary=summary, memories=memory_responses(memories)
    )


@app.post("/api/session/{session_id}/summarize", response_model=SummaryResponse)
def summarize_session(session_id: str, db: DbSession):
    if not settings.openai_api_key:
        raise api_error(503, "provider_not_configured", "OpenAI is not configured on the server.", True)
    try:
        summary, memories = therapy.summarize(db, session_id)
    except LookupError as error:
        raise api_error(404, "session_not_found", str(error)) from error
    except Exception as error:
        logger.exception("Summary failed")
        raise api_error(502, "summary_failed", "Could not summarize the session.", True) from error
    return SummaryResponse(session_id=session_id, summary=summary, memories=memory_responses(memories))


@app.delete("/api/session/{session_id}", status_code=204)
def delete_session(session_id: str, db: DbSession):
    record = db.get(TherapySession, session_id)
    if not record:
        raise api_error(404, "session_not_found", "Session not found.")
    for audio in db.scalars(select(AudioLog).where(AudioLog.session_id == session_id)).all():
        Path(audio.file_path).unlink(missing_ok=True)
    vector_memory.delete_session(session_id)
    for memory in db.scalars(select(Memory).where(Memory.source_session_id == session_id)).all():
        db.delete(memory)
    summary = db.scalar(select(SessionSummary).where(SessionSummary.session_id == session_id))
    if summary:
        db.delete(summary)
    for continuity_record in db.scalars(
        select(LongitudinalRecord).where(LongitudinalRecord.source_session_id == session_id)
    ).all():
        db.delete(continuity_record)
    for audio in db.scalars(select(AudioLog).where(AudioLog.session_id == session_id)).all():
        db.delete(audio)
    language = record.language
    db.delete(record)
    db.commit()
    therapy.rebuild_profile_from_storage(db, language)
    return None


@app.delete("/api/memory/{memory_id}", status_code=204)
def delete_memory(memory_id: str, db: DbSession):
    record = db.get(Memory, memory_id)
    if not record:
        raise api_error(404, "memory_not_found", "Memory not found.")
    vector_memory.delete(memory_id)
    db.delete(record)
    db.commit()
    return None


@app.get("/api/memory/search")
def search_memory(q: str, db: DbSession, top_k: int = 8):
    del db
    if not settings.memory_debug_enabled:
        raise api_error(404, "not_found", "Not found.")
    try:
        results = vector_memory.search(
            q, persona_loader.load().language, max(1, min(top_k, 30)), 0
        )
    except Exception as error:
        raise api_error(503, "memory_unavailable", "Memory search is unavailable.", True) from error
    return {"results": results}


@app.get("/", include_in_schema=False)
def frontend_index():
    return FileResponse(PROJECT_ROOT / "index.html", media_type="text/html")


@app.get("/styles.css", include_in_schema=False)
def frontend_styles():
    return FileResponse(PROJECT_ROOT / "styles.css", media_type="text/css")


app.mount("/src", StaticFiles(directory=PROJECT_ROOT / "src"), name="frontend-src")
app.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "assets"), name="frontend-assets")
