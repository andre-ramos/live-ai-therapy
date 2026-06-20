import json
import os
import tempfile
from pathlib import Path

TEST_ROOT = Path(tempfile.mkdtemp(prefix="live-therapy-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'test.db'}"
os.environ["VECTOR_DB_PATH"] = str(TEST_ROOT / "chroma")
os.environ["AUDIO_TMP_PATH"] = str(TEST_ROOT / "audio")
os.environ["OPENAI_API_KEY"] = "test-openai"
os.environ["ELEVENLABS_API_KEY"] = "test-elevenlabs"
os.environ["ELEVENLABS_VOICE_ID"] = "test-voice"

from fastapi.testclient import TestClient

from backend.app import main


class FakeProvider:
    def transcribe(self, _path, _language):
        return "Eu me senti ansioso hoje."

    def generate(self, system_prompt, _conversation, _temperature):
        if "strict JSON" in system_prompt:
            return json.dumps({
                "summary": "Falamos sobre ansiedade e respiração.",
                "memories": [{
                    "memory_type": "goal",
                    "content": "Praticar respiração antes de reuniões.",
                    "importance": 0.8,
                    "source_message_ids": [],
                }],
                "topics": [{
                    "title": "Ansiedade antes de reuniões",
                    "content": "A ansiedade aparece antes de reuniões de trabalho.",
                    "status": "active",
                    "confidence": 0.8,
                    "importance": 0.8,
                    "follow_up_question": "Como foi a próxima reunião?",
                    "source_message_ids": [],
                }],
            })
        return "Entendo. Vamos observar com calma o que aconteceu?"

    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    def synthesize(self, _text, _voice_id, _model, _language, _speed):
        return b"ID3-fake-mp3"


class FakeVectorMemory:
    ready = True

    def initialize(self):
        return None

    def search(self, *_args):
        return []

    def search_archive(self, *_args):
        return []

    def add(self, *_args):
        return None

    def delete(self, *_args):
        return None

    def delete_session(self, *_args):
        return None


fake = FakeProvider()
main.vector_memory = FakeVectorMemory()
main.therapy.stt = fake
main.therapy.llm = fake
main.therapy.tts = fake
main.therapy.vector_memory = main.vector_memory


def test_complete_session_api_flow():
    with TestClient(main.app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["database"] == "ready"

        persona = client.get("/api/persona")
        assert persona.status_code == 200
        assert persona.json()["language"] == "pt-BR"
        assert persona.json()["image_url"].startswith("/api/persona/image?v=")
        assert "voice_id" not in persona.json()

        portrait = client.get(persona.json()["image_url"])
        assert portrait.status_code == 200
        assert portrait.headers["content-type"].startswith("image/jpeg")

        legacy_portrait = client.get("/assets/sandy.jpg")
        assert legacy_portrait.status_code == 200
        assert legacy_portrait.content == portrait.content

        started = client.post("/api/session/start", json={})
        assert started.status_code == 201
        session_id = started.json()["session_id"]
        assert started.json()["psychologist_name"] == "Sandy"
        assert started.json()["language"] == "pt-BR"
        assert started.json()["persona_version"] == 3
        assert len(started.json()["persona_hash"]) == 64

        turn = client.post(
            "/api/voice-turn",
            data={"session_id": session_id},
            files={"audio": ("utterance.webm", b"fake-audio", "audio/webm")},
        )
        assert turn.status_code == 200
        assert turn.json()["assistant_text"].startswith("Entendo")
        assert turn.json()["audio_url"]

        audio = client.get(turn.json()["audio_url"])
        assert audio.status_code == 200
        assert audio.headers["content-type"].startswith("audio/mpeg")

        messages = client.get(f"/api/session/{session_id}/messages")
        assert [item["role"] for item in messages.json()["messages"]] == ["user", "assistant"]

        ended = client.post(f"/api/session/{session_id}/end")
        assert ended.status_code == 200
        assert "ansiedade" in ended.json()["summary"]
        memory_id = ended.json()["memories"][0]["memory_id"]

        assert client.delete(f"/api/memory/{memory_id}").status_code == 204
        assert client.delete(f"/api/session/{session_id}").status_code == 204
        assert client.get(f"/api/session/{session_id}/messages").status_code == 404


def test_validation_and_private_debug_endpoint():
    with TestClient(main.app) as client:
        mismatch = client.post("/api/session/start", json={"language": "en-US"})
        assert mismatch.status_code == 422
        assert mismatch.json()["code"] == "persona_language_mismatch"
        assert client.get("/api/memory/search", params={"q": "private"}).status_code == 404
        assert client.post(
            "/api/voice-turn",
            data={"session_id": "missing"},
            files={"audio": ("utterance.webm", b"audio", "audio/webm")},
        ).status_code == 404


def test_voice_turn_rejects_language_override():
    with TestClient(main.app) as client:
        session_id = client.post("/api/session/start", json={}).json()["session_id"]
        response = client.post(
            "/api/voice-turn",
            data={"session_id": session_id, "language_override": "en-US"},
            files={"audio": ("utterance.webm", b"audio", "audio/webm")},
        )
        assert response.status_code == 422
        assert response.json()["code"] == "persona_language_mismatch"
