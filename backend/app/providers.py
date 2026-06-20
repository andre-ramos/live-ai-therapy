from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx
from openai import OpenAI


class SpeechToTextProvider(Protocol):
    def transcribe(self, audio_path: Path, language: str) -> str: ...


class LanguageModelProvider(Protocol):
    def generate(self, system_prompt: str, conversation: list[dict[str, str]], temperature: float) -> str: ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class TextToSpeechProvider(Protocol):
    def synthesize(
        self, text: str, voice_id: str, model: str, language: str, speed: float
    ) -> bytes: ...


@dataclass
class OpenAIProviders(SpeechToTextProvider, LanguageModelProvider, EmbeddingProvider):
    api_key: str
    stt_model: str
    llm_model: str
    embedding_model: str

    def __post_init__(self) -> None:
        self.client = OpenAI(api_key=self.api_key, timeout=90, max_retries=2)

    def transcribe(self, audio_path: Path, language: str) -> str:
        language_hint = {"pt-BR": "pt", "en-US": "en"}.get(language, "pt")
        with audio_path.open("rb") as audio:
            response = self.client.audio.transcriptions.create(
                model=self.stt_model,
                file=audio,
                language=language_hint,
            )
        return response.text.strip()

    def generate(self, system_prompt: str, conversation: list[dict[str, str]], temperature: float) -> str:
        input_messages = [{"role": "system", "content": system_prompt}, *conversation]
        response = self.client.responses.create(
            model=self.llm_model,
            input=input_messages,
            temperature=temperature,
            store=False,
        )
        return response.output_text.strip()

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.embedding_model, input=texts)
        return [item.embedding for item in response.data]


@dataclass
class ElevenLabsProvider(TextToSpeechProvider):
    api_key: str

    def synthesize(
        self, text: str, voice_id: str, model: str, language: str, speed: float
    ) -> bytes:
        language_code = {"pt-BR": "pt", "en-US": "en"}.get(language)
        if not language_code:
            raise ValueError("Unsupported ElevenLabs language")
        response = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": self.api_key, "Accept": "audio/mpeg"},
            json={
                "text": text,
                "model_id": model,
                "language_code": language_code,
                "voice_settings": {
                    "stability": 0.55,
                    "similarity_boost": 0.75,
                    "speed": speed,
                },
            },
            timeout=90,
        )
        response.raise_for_status()
        return response.content


class UnconfiguredProvider:
    def _raise(self) -> None:
        raise RuntimeError("External providers are not configured")

    def transcribe(self, audio_path: Path, language: str) -> str:
        self._raise()

    def generate(self, system_prompt: str, conversation: list[dict[str, str]], temperature: float) -> str:
        self._raise()

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._raise()

    def synthesize(
        self, text: str, voice_id: str, model: str, language: str, speed: float
    ) -> bytes:
        self._raise()
