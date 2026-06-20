from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'app.db'}"
    vector_db_path: str = str(PROJECT_ROOT / "data" / "chroma")
    audio_tmp_path: str = str(PROJECT_ROOT / "data" / "audio_tmp")
    debug_store_audio: bool = False
    memory_debug_enabled: bool = False
    generated_audio_ttl_seconds: int = 600
    persona_file: str = ""

    @property
    def providers_ready(self) -> bool:
        return bool(self.openai_api_key and self.elevenlabs_api_key and self.elevenlabs_voice_id)


class SessionConfig(BaseModel):
    supported_languages: list[str] = ["pt-BR", "en-US"]
    default_duration_minutes: int = 60

class PersonaConfig(BaseModel):
    file: str = "config/personas/sandy.md"
    max_bytes: int = Field(default=65_536, ge=1_024, le=1_048_576)


class DefaultTopics(BaseModel):
    enabled: bool = True
    use_when_user_does_not_define_topic: bool = True
    topics: dict[str, list[str]]


class RagConfig(BaseModel):
    enabled: bool = True
    retrieve_past_sessions: bool = True
    top_k: int = Field(default=8, ge=1, le=30)
    similarity_threshold: float = Field(default=0.72, ge=0, le=1)


class ConversationConfig(BaseModel):
    recent_messages_to_include: int = Field(default=12, ge=1, le=50)
    summarize_session_on_end: bool = True
    extract_memories_on_end: bool = True


class LongTermMemoryConfig(BaseModel):
    enabled: bool = True
    recent_session_count: int = Field(default=5, ge=1, le=20)
    archive_top_k: int = Field(default=3, ge=1, le=10)
    archive_similarity_threshold: float = Field(default=0.72, ge=0, le=1)
    rebuild_every_sessions: int = Field(default=10, ge=2, le=100)
    trigger_phrases: dict[str, list[str]]


class ProviderModelConfig(BaseModel):
    provider: str
    model: str


class LlmConfig(ProviderModelConfig):
    temperature: float = Field(default=0.7, ge=0, le=2)


class TtsConfig(BaseModel):
    speed: float = Field(default=1.0, ge=0.7, le=1.2)


class VadConfig(BaseModel):
    minimum_recording_ms: int = 500
    silence_duration_ms: int = 1000
    maximum_recording_ms: int = 45000
    post_playback_delay_ms: int = 500


class EmergencyConfig(BaseModel):
    pt_BR: list[str]
    en_US: list[str]

    def for_language(self, language: str) -> list[str]:
        return {"pt-BR": self.pt_BR, "en-US": self.en_US}.get(language, [])


class AppConfig(BaseModel):
    session: SessionConfig
    persona: PersonaConfig
    default_topics: DefaultTopics
    rag_memory: RagConfig
    conversation: ConversationConfig
    long_term_memory: LongTermMemoryConfig
    vad: VadConfig
    stt: ProviderModelConfig
    llm: LlmConfig
    embeddings: ProviderModelConfig
    tts: TtsConfig
    emergency: EmergencyConfig

    def model_post_init(self, __context: Any) -> None:
        missing_topics = set(self.session.supported_languages) - set(self.default_topics.topics)
        if missing_topics:
            raise ValueError(f"missing default topics for: {sorted(missing_topics)}")
        missing_emergency = [
            language for language in self.session.supported_languages
            if not self.emergency.for_language(language)
        ]
        if missing_emergency:
            raise ValueError(f"missing emergency guidance for: {sorted(missing_emergency)}")
        missing_triggers = set(self.session.supported_languages) - set(self.long_term_memory.trigger_phrases)
        if missing_triggers:
            raise ValueError(f"missing long-term memory triggers for: {sorted(missing_triggers)}")


@lru_cache
def load_app_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path else PROJECT_ROOT / "config" / "psychologist.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return AppConfig.model_validate(raw)


@lru_cache
def load_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings()
