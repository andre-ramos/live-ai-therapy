from pathlib import Path

import pytest

from backend.app.config import RuntimeSettings, load_app_config
from backend.app.persona import PersonaLoader, PersonaUnavailableError


def test_persona_is_reloaded_but_each_snapshot_is_immutable(tmp_path: Path):
    persona_dir = tmp_path / "config" / "personas"
    persona_dir.mkdir(parents=True)
    config = load_app_config().model_copy(deep=True)
    config.persona.file = "config/personas/test.md"
    settings = RuntimeSettings(elevenlabs_voice_id="voice-pt")
    _write_reference(tmp_path)
    path = persona_dir / "test.md"
    path.write_text(_persona("Calma e acolhedora."), encoding="utf-8")
    loader = PersonaLoader(config, settings, project_root=tmp_path)

    first = loader.load()
    path.write_text(_persona("Direta e gentil.", version=2), encoding="utf-8")
    second = loader.load()

    assert first.version == 1
    assert "Calma" in first.markdown
    assert second.version == 2
    assert "Direta" in second.markdown
    assert first.content_hash != second.content_hash
    assert first.image_path.name == "Sandy.jpeg"
    assert len(first.image_hash) == 64
    assert first.image_media_type == "image/jpeg"
    assert first.approach_source == "psychologist_approaches_bilingual.md"
    assert "## 1. CBT / TCC" in first.approach_markdown
    assert "## 4. DBT" not in first.approach_markdown


def test_approach_reference_changes_next_snapshot_only(tmp_path: Path):
    persona_dir = tmp_path / "config" / "personas"
    persona_dir.mkdir(parents=True)
    config = load_app_config().model_copy(deep=True)
    config.persona.file = "config/personas/test.md"
    (persona_dir / "test.md").write_text(_persona("Calma e acolhedora."), encoding="utf-8")
    reference = _write_reference(tmp_path)
    loader = PersonaLoader(
        config, RuntimeSettings(elevenlabs_voice_id="voice-pt"), project_root=tmp_path
    )

    first = loader.load()
    reference.write_text(reference.read_text(encoding="utf-8").replace(
        "Princípios de TCC.", "Princípios de TCC revisados."
    ), encoding="utf-8")
    second = loader.load()

    assert "revisados" not in first.approach_markdown
    assert "revisados" in second.approach_markdown
    assert first.approach_hash != second.approach_hash
    assert first.content_hash != second.content_hash


@pytest.mark.parametrize("content", ["", "# no front matter", "---\nlanguage: pt-BR\n---\nshort"])
def test_invalid_persona_is_rejected(tmp_path: Path, content: str):
    persona_dir = tmp_path / "config" / "personas"
    persona_dir.mkdir(parents=True)
    config = load_app_config().model_copy(deep=True)
    config.persona.file = "config/personas/test.md"
    (persona_dir / "test.md").write_text(content, encoding="utf-8")
    with pytest.raises(PersonaUnavailableError):
        PersonaLoader(
            config, RuntimeSettings(elevenlabs_voice_id="voice-pt"), project_root=tmp_path
        ).load()


def test_missing_voice_is_rejected(tmp_path: Path):
    persona_dir = tmp_path / "config" / "personas"
    persona_dir.mkdir(parents=True)
    config = load_app_config().model_copy(deep=True)
    config.persona.file = "config/personas/test.md"
    (persona_dir / "test.md").write_text(_persona("Calma e acolhedora."), encoding="utf-8")
    with pytest.raises(PersonaUnavailableError, match="voice"):
        PersonaLoader(config, RuntimeSettings(elevenlabs_voice_id=""), project_root=tmp_path).load()


def test_persona_path_cannot_escape_directory(tmp_path: Path):
    config = load_app_config().model_copy(deep=True)
    config.persona.file = "outside.md"
    with pytest.raises(PersonaUnavailableError):
        PersonaLoader(config, RuntimeSettings(elevenlabs_voice_id="voice-pt"), project_root=tmp_path)


def test_persona_image_path_cannot_escape_directory(tmp_path: Path):
    persona_dir = tmp_path / "config" / "personas"
    persona_dir.mkdir(parents=True)
    config = load_app_config().model_copy(deep=True)
    config.persona.file = "config/personas/test.md"
    _write_reference(tmp_path)
    content = _persona("Calma e acolhedora.").replace("image_file: Sandy.jpeg", "image_file: ../outside.jpeg")
    (persona_dir / "test.md").write_text(content, encoding="utf-8")
    with pytest.raises(PersonaUnavailableError, match="image"):
        PersonaLoader(
            config, RuntimeSettings(elevenlabs_voice_id="voice-pt"), project_root=tmp_path
        ).load()


def test_public_persona_can_load_project_asset(tmp_path: Path):
    persona_dir = tmp_path / "config" / "personas"
    persona_dir.mkdir(parents=True)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "sandy.jpg").write_bytes(b"public-image")
    config = load_app_config().model_copy(deep=True)
    config.persona.file = "config/personas/test.md"
    _write_reference(tmp_path)
    content = _persona("Calma e acolhedora.").replace(
        "image_file: Sandy.jpeg", "image_file: assets/sandy.jpg"
    )
    (persona_dir / "test.md").write_text(content, encoding="utf-8")

    snapshot = PersonaLoader(
        config, RuntimeSettings(elevenlabs_voice_id="voice-pt"), project_root=tmp_path
    ).load()

    assert snapshot.image_path == tmp_path / "assets" / "sandy.jpg"


def test_runtime_persona_override_keeps_private_persona_local(tmp_path: Path):
    persona_dir = tmp_path / "config" / "personas"
    persona_dir.mkdir(parents=True)
    config = load_app_config().model_copy(deep=True)
    _write_reference(tmp_path)
    (persona_dir / "public.md").write_text(_persona("PÃºblica."), encoding="utf-8")
    (persona_dir / "sandy.local.md").write_text(_persona("Privada."), encoding="utf-8")
    config.persona.file = "config/personas/public.md"

    snapshot = PersonaLoader(
        config,
        RuntimeSettings(
            elevenlabs_voice_id="voice-pt",
            persona_file="config/personas/sandy.local.md",
        ),
        project_root=tmp_path,
    ).load()

    assert "Privada" in snapshot.markdown


def _persona(description: str, version: int = 1) -> str:
    padding = " Esta descrição mantém comportamento consistente e seguro durante toda a sessão." * 2
    return f"""---
id: sandy
version: {version}
display_name: Sandy
role: virtual_psychological_support_assistant
language: pt-BR
image_file: Sandy.jpeg
approaches: [CBT, ACT, CFT]
approaches_file: psychologist_approaches_bilingual.md
voice_id_env: ELEVENLABS_VOICE_ID
voice_model: eleven_multilingual_v2
---
# Identidade
{description}{padding}
"""


def _write_reference(root: Path) -> Path:
    (root / "config" / "personas" / "Sandy.jpeg").write_bytes(b"fake-jpeg-image")
    path = root / "psychologist_approaches_bilingual.md"
    path.write_text("""# Referência

## 1. CBT / TCC — Cognitive Behavioral Therapy / Terapia Cognitivo-Comportamental
Princípios de TCC.

## 2. ACT — Acceptance and Commitment Therapy / Terapia de Aceitação e Compromisso
Princípios de ACT.

## 3. CFT — Compassion Focused Therapy / Terapia Focada na Compaixão
Princípios de CFT.

## 4. DBT Skills — Dialectical Behavior Therapy Skills / Habilidades de DBT
Princípios de DBT.
""", encoding="utf-8")
    return path
