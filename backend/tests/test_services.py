from backend.app.config import RuntimeSettings, load_app_config
from backend.app.persona import PersonaLoader
from backend.app.providers import ElevenLabsProvider
from backend.app.services import (
    build_opening_prompt,
    build_summary_prompt,
    build_system_prompt,
    clean_for_speech,
    contains_imminent_risk,
    crisis_guidance,
)


def test_configuration_and_prompt_use_sandy_and_selected_approaches():
    config = load_app_config()
    assert config.tts.speed == 1.0
    persona = PersonaLoader(config, RuntimeSettings(elevenlabs_voice_id="test-voice")).load()
    prompt = build_system_prompt(config, persona, [{"content": "A pessoa prefere exercícios curtos."}])
    assert "Sandy" in prompt
    assert "TCC" in prompt
    assert "ACT" in prompt
    assert "A pessoa prefere exercícios curtos" in prompt
    assert "diagnostique" in prompt
    assert "exclusivamente em português brasileiro" in prompt
    assert "não faça pergunta nenhuma" in prompt
    assert persona.markdown in prompt
    assert persona.approach_markdown in prompt
    assert persona.approach_source == "psychologist_approaches_bilingual.md"
    assert "CBT / TCC" in persona.approach_markdown
    assert "DBT Skills" not in persona.approach_markdown


def test_opening_prompt_prefers_single_prior_thread_and_therapist_first_language():
    config = load_app_config()
    persona = PersonaLoader(config, RuntimeSettings(elevenlabs_voice_id="test-voice")).load()
    prompt = build_opening_prompt(config, persona, {
        "recent_session_ids": ["session-new", "session-old"],
        "active_records": [
            {
                "status": "deferred",
                "importance": 0.9,
                "source_session_id": "session-old",
                "title": "Conversa com a mãe",
            },
            {
                "status": "active",
                "importance": 0.8,
                "source_session_id": "session-new",
                "title": "Ansiedade no trabalho",
            },
        ],
    })
    assert "Você fala primeiro nesta sessão" in prompt
    assert "saudação breve e acolhedora" in prompt
    assert "exatamente uma pergunta aberta no final" in prompt
    assert '"title": "Ansiedade no trabalho"' in prompt
    assert '"title": "Conversa com a mãe"' not in prompt


def test_foundation_session_prompts_use_intake_guidance():
    config = load_app_config()
    persona = PersonaLoader(config, RuntimeSettings(elevenlabs_voice_id="test-voice")).load()
    opening = build_opening_prompt(config, persona, {}, is_foundation_session=True)
    assert "SESSÃO FUNDACIONAL" in opening
    assert "<foundation_session_guidelines>" in opening
    assert "primeira consulta tem como principal objetivo" in opening
    assert "Faça exatamente uma pergunta aberta no final" in opening

    system = build_system_prompt(config, persona, [], {}, is_foundation_session=True)
    assert "sessão fundacional" in system
    assert "vínculo terapêutico" in system
    assert "expectativa" in system


def test_foundation_session_summary_prompt_preserves_intake_context():
    prompt = build_summary_prompt([], "en-US", ["CBT"], is_foundation_session=True)[0]["content"]
    assert "foundation session for future continuity" in prompt
    assert "presenting complaint" in prompt
    assert "support/resources" in prompt
    assert "initial agreements" in prompt


def test_elevenlabs_request_uses_configured_speed(monkeypatch):
    captured = {}

    class Response:
        content = b"audio"

        @staticmethod
        def raise_for_status():
            return None

    def fake_post(_url, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    monkeypatch.setattr("backend.app.providers.httpx.post", fake_post)
    result = ElevenLabsProvider("test-key").synthesize(
        "Olá", "voice-id", "eleven_multilingual_v2", "pt-BR", 0.9
    )
    assert result == b"audio"
    assert captured["voice_settings"]["speed"] == 0.9


def test_speech_cleanup_removes_markdown_and_links():
    assert clean_for_speech("**Olá** [site](https://example.com)\n\nTudo bem?") == "Olá site Tudo bem?"


def test_crisis_guidance_is_deterministic_and_localized():
    config = load_app_config()
    assert contains_imminent_risk("Eu quero me matar")
    guidance = crisis_guidance("pt-BR", config)
    assert "192" in guidance
    assert "188" in guidance
    assert not contains_imminent_risk("Estou triste hoje")
