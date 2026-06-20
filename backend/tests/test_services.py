from backend.app.config import RuntimeSettings, load_app_config
from backend.app.persona import PersonaLoader
from backend.app.providers import ElevenLabsProvider
from backend.app.services import build_system_prompt, clean_for_speech, contains_imminent_risk, crisis_guidance


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
    assert persona.markdown in prompt
    assert persona.approach_markdown in prompt
    assert persona.approach_source == "psychologist_approaches_bilingual.md"
    assert "CBT / TCC" in persona.approach_markdown
    assert "DBT Skills" not in persona.approach_markdown


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
