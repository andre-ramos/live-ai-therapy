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
        if '{"assistant_text":"...","topics_to_add":["..."],"end_session":false,"end_reason":null}' in system_prompt:
            return json.dumps({
                "assistant_text": "Entendo. Isso parece ter pesado bastante em você hoje.",
                "topics_to_add": ["Ansiedade no trabalho"],
                "end_session": False,
                "end_reason": None,
            })
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
        if "REGISTRO PRIORITÁRIO PARA A ABERTURA DE HOJE" in system_prompt:
            return "Quero começar te ouvindo com calma hoje. Como as coisas têm pesado em você ultimamente?"
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

    def reset(self):
        return None


fake = FakeProvider()
main.vector_memory = FakeVectorMemory()
main.therapy.stt = fake
main.therapy.llm = fake
main.therapy.tts = fake
main.therapy.vector_memory = main.vector_memory


def reset_session_storage():
    main.database.create_all()
    with main.database.session_factory() as db:
        for model in (
            main.AudioLog,
            main.Memory,
            main.LongitudinalRecord,
            main.SessionSummary,
            main.Message,
            main.TherapySession,
            main.LongitudinalProfile,
        ):
            db.query(model).delete()
        db.commit()


def test_complete_session_api_flow():
    reset_session_storage()
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
        assert started.json()["assistant_text"].startswith("Quero começar")
        assert started.json()["audio_url"]
        assert started.json()["vad"]["silence_duration_ms"] == 1800
        assert started.json()["vad"]["idle_warning_ms"] == 45000
        assert started.json()["vad"]["idle_end_ms"] == 60000
        with main.database.session_factory() as db:
            record = db.get(main.TherapySession, session_id)
            assert record.is_foundation_session is True

        opening_audio = client.get(started.json()["audio_url"])
        assert opening_audio.status_code == 200
        assert opening_audio.headers["content-type"].startswith("audio/mpeg")

        turn = client.post(
            "/api/voice-turn",
            data={"session_id": session_id},
            files={"audio": ("utterance.webm", b"fake-audio", "audio/webm")},
        )
        assert turn.status_code == 200
        assert turn.json()["assistant_text"].startswith("Entendo")
        assert turn.json()["audio_url"]
        assert turn.json()["topics_to_add"] == ["Ansiedade no trabalho"]
        assert turn.json()["end_session"] is False
        assert turn.json()["end_reason"] is None

        audio = client.get(turn.json()["audio_url"])
        assert audio.status_code == 200
        assert audio.headers["content-type"].startswith("audio/mpeg")

        messages = client.get(f"/api/session/{session_id}/messages")
        assert [item["role"] for item in messages.json()["messages"]] == ["assistant", "user", "assistant"]

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


def test_delete_history_clears_all_session_data():
    reset_session_storage()
    with TestClient(main.app) as client:
        session_id = client.post("/api/session/start", json={}).json()["session_id"]
        assert client.post(
            "/api/voice-turn",
            data={"session_id": session_id},
            files={"audio": ("utterance.webm", b"fake-audio", "audio/webm")},
        ).status_code == 200
        assert client.post(f"/api/session/{session_id}/end").status_code == 200
        assert client.delete("/api/history").status_code == 204
        with main.database.session_factory() as db:
            assert db.query(main.TherapySession).count() == 0
            assert db.query(main.Message).count() == 0
            assert db.query(main.SessionSummary).count() == 0
            assert db.query(main.Memory).count() == 0
            assert db.query(main.LongitudinalRecord).count() == 0
            assert db.query(main.LongitudinalProfile).count() == 0
            assert db.query(main.AudioLog).count() == 0


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


def test_voice_turn_can_request_session_end():
    class EndingProvider(FakeProvider):
        def transcribe(self, _path, _language):
            return "Podemos encerrar por aqui hoje."

        def generate(self, system_prompt, _conversation, _temperature):
            if '{"assistant_text":"...","topics_to_add":["..."],"end_session":false,"end_reason":null}' in system_prompt:
                return json.dumps({
                    "assistant_text": "Tudo bem. Vamos encerrar por aqui por hoje.",
                    "topics_to_add": [],
                    "end_session": True,
                    "end_reason": "user_request",
                })
            return super().generate(system_prompt, _conversation, _temperature)

    ending = EndingProvider()
    main.therapy.stt = ending
    main.therapy.llm = ending
    try:
        with TestClient(main.app) as client:
            session_id = client.post("/api/session/start", json={}).json()["session_id"]
            response = client.post(
                "/api/voice-turn",
                data={"session_id": session_id},
                files={"audio": ("utterance.webm", b"audio", "audio/webm")},
            )
            assert response.status_code == 200
            assert response.json()["end_session"] is True
            assert response.json()["end_reason"] == "user_request"
    finally:
        main.therapy.stt = fake
        main.therapy.llm = fake


def test_session_start_succeeds_without_provider_backends():
    old_key = main.settings.openai_api_key
    main.settings.openai_api_key = ""
    try:
        with TestClient(main.app) as client:
            response = client.post("/api/session/start", json={})
            assert response.status_code == 201
            assert response.json()["assistant_text"] is None
            assert response.json()["audio_url"] is None
    finally:
        main.settings.openai_api_key = old_key


def test_only_first_same_language_session_is_marked_as_foundation():
    reset_session_storage()
    with TestClient(main.app) as client:
        first_session_id = client.post("/api/session/start", json={}).json()["session_id"]
        assert client.post(f"/api/session/{first_session_id}/end").status_code == 200

        second_session_id = client.post("/api/session/start", json={}).json()["session_id"]
        with main.database.session_factory() as db:
            first = db.get(main.TherapySession, first_session_id)
            second = db.get(main.TherapySession, second_session_id)
            assert first.is_foundation_session is True
            assert second.is_foundation_session is False
