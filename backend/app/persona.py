from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from .approaches import ApproachReferenceError, ApproachReferenceLoader
from .config import AppConfig, PROJECT_ROOT, RuntimeSettings

FRONT_MATTER = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)\Z", re.DOTALL)
SAFE_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
MAX_PERSONA_IMAGE_BYTES = 10 * 1024 * 1024


class PersonaUnavailableError(RuntimeError):
    pass


class PersonaLanguageMismatchError(ValueError):
    pass


class PersonaMetadata(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    version: int = Field(ge=1)
    display_name: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=100)
    language: str
    image_file: str = Field(min_length=1, max_length=255)
    approaches: list[str] = Field(min_length=1)
    approaches_file: str = Field(min_length=1, max_length=255)
    voice_id_env: str
    voice_model: str = Field(min_length=1, max_length=100)

    @field_validator("approaches")
    @classmethod
    def validate_approaches(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values if value.strip()]
        if not normalized or len(set(normalized)) != len(normalized):
            raise ValueError("approaches must be non-empty and unique")
        return normalized

    @field_validator("voice_id_env")
    @classmethod
    def validate_voice_environment_name(cls, value: str) -> str:
        if not SAFE_ENV_NAME.fullmatch(value):
            raise ValueError("voice_id_env must be an environment variable name")
        return value


@dataclass(frozen=True)
class PersonaSnapshot:
    id: str
    version: int
    display_name: str
    role: str
    language: str
    approaches: list[str]
    approach_source: str
    approach_hash: str
    approach_markdown: str
    voice_id: str
    voice_model: str
    markdown: str
    content_hash: str
    image_path: Path | None = None
    image_hash: str = ""
    image_media_type: str = "image/jpeg"


class PersonaLoader:
    def __init__(self, config: AppConfig, settings: RuntimeSettings, project_root: Path = PROJECT_ROOT):
        self.config = config
        self.settings = settings
        self.project_root = project_root.resolve()
        self.approach_loader = ApproachReferenceLoader(self.project_root)
        persona_root = (project_root / "config" / "personas").resolve()
        persona_file = settings.persona_file.strip() or config.persona.file
        configured_path = (project_root / persona_file).resolve()
        if configured_path.parent != persona_root:
            raise PersonaUnavailableError("Persona file must be inside config/personas.")
        self.path = configured_path

    def load(self) -> PersonaSnapshot:
        try:
            size = self.path.stat().st_size
            if size > self.config.persona.max_bytes:
                raise PersonaUnavailableError("Persona file exceeds the configured size limit.")
            raw = self.path.read_text(encoding="utf-8")
        except PersonaUnavailableError:
            raise
        except (OSError, UnicodeError) as error:
            raise PersonaUnavailableError("Persona file could not be read as UTF-8.") from error

        match = FRONT_MATTER.fullmatch(raw)
        if not match:
            raise PersonaUnavailableError("Persona file requires valid YAML front matter.")
        try:
            metadata = PersonaMetadata.model_validate(yaml.safe_load(match.group(1)) or {})
        except (yaml.YAMLError, ValidationError) as error:
            raise PersonaUnavailableError("Persona metadata is invalid.") from error

        markdown_body = match.group(2).strip()
        if len(markdown_body) < 100:
            raise PersonaUnavailableError("Persona description is incomplete.")
        if metadata.language not in self.config.session.supported_languages:
            raise PersonaUnavailableError("Persona language is not supported by the application.")
        if not self.config.default_topics.topics.get(metadata.language):
            raise PersonaUnavailableError("Persona language has no configured default topics.")
        if not self.config.emergency.for_language(metadata.language):
            raise PersonaUnavailableError("Persona language has no emergency guidance.")

        voice_id = self._resolve_voice_id(metadata.voice_id_env)
        if not voice_id:
            raise PersonaUnavailableError("Persona voice is not configured.")
        image_path, image_hash, image_media_type = self._load_image(metadata.image_file)
        try:
            approach_reference = self.approach_loader.load(
                metadata.approaches_file, metadata.approaches
            )
        except ApproachReferenceError as error:
            raise PersonaUnavailableError(str(error)) from error
        combined_hash = hashlib.sha256(
            f"{raw}\n{approach_reference.source}\n{approach_reference.markdown}".encode("utf-8")
        ).hexdigest()
        return PersonaSnapshot(
            id=metadata.id,
            version=metadata.version,
            display_name=metadata.display_name,
            role=metadata.role,
            language=metadata.language,
            image_path=image_path,
            image_hash=image_hash,
            image_media_type=image_media_type,
            approaches=metadata.approaches,
            approach_source=approach_reference.source,
            approach_hash=approach_reference.content_hash,
            approach_markdown=approach_reference.markdown,
            voice_id=voice_id,
            voice_model=metadata.voice_model,
            markdown=markdown_body,
            content_hash=combined_hash,
        )

    def _load_image(self, configured_file: str) -> tuple[Path, str, str]:
        persona_root = (self.project_root / "config" / "personas").resolve()
        assets_root = (self.project_root / "assets").resolve()
        configured_path = Path(configured_file)
        if configured_path.is_absolute():
            raise PersonaUnavailableError("Persona image must use a project-relative path.")
        if len(configured_path.parts) == 1:
            image_path = (persona_root / configured_path).resolve()
            allowed_root = persona_root
        else:
            image_path = (self.project_root / configured_path).resolve()
            allowed_root = assets_root
        if image_path.parent != allowed_root:
            raise PersonaUnavailableError("Persona image must be directly inside assets or config/personas.")
        media_type = IMAGE_MEDIA_TYPES.get(image_path.suffix.lower())
        if not media_type:
            raise PersonaUnavailableError("Persona image must be JPEG, PNG, or WebP.")
        try:
            if image_path.stat().st_size > MAX_PERSONA_IMAGE_BYTES:
                raise PersonaUnavailableError("Persona image exceeds the 10 MB size limit.")
            image_bytes = image_path.read_bytes()
        except PersonaUnavailableError:
            raise
        except OSError as error:
            raise PersonaUnavailableError("Persona image could not be read.") from error
        if not image_bytes:
            raise PersonaUnavailableError("Persona image is empty.")
        return image_path, hashlib.sha256(image_bytes).hexdigest(), media_type

    def _resolve_voice_id(self, environment_name: str) -> str:
        if environment_name == "ELEVENLABS_VOICE_ID":
            return self.settings.elevenlabs_voice_id.strip()
        return os.getenv(environment_name, "").strip()
