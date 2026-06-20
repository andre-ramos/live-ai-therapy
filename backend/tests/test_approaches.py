from pathlib import Path

import pytest

from backend.app.approaches import ApproachReferenceError, ApproachReferenceLoader


REFERENCE = """# Reference

## 1. CBT / TCC — Cognitive Behavioral Therapy / Terapia Cognitivo-Comportamental
CBT content.

## 2. ACT — Acceptance and Commitment Therapy / Terapia de Aceitação e Compromisso
ACT content.

## 3. CFT — Compassion Focused Therapy / Terapia Focada na Compaixão
CFT content.

## 4. DBT Skills — Dialectical Behavior Therapy Skills / Habilidades de DBT
DBT content.
"""


def test_loads_only_selected_sections_in_configured_order(tmp_path: Path):
    (tmp_path / "approaches.md").write_text(REFERENCE, encoding="utf-8")

    result = ApproachReferenceLoader(tmp_path).load("approaches.md", ["CFT", "CBT"])

    assert result.source == "approaches.md"
    assert result.markdown.index("CFT content") < result.markdown.index("CBT content")
    assert "ACT content" not in result.markdown
    assert "DBT content" not in result.markdown
    assert len(result.content_hash) == 64


def test_rejects_selected_approach_missing_from_reference(tmp_path: Path):
    (tmp_path / "approaches.md").write_text(REFERENCE, encoding="utf-8")

    with pytest.raises(ApproachReferenceError, match="missing"):
        ApproachReferenceLoader(tmp_path).load("approaches.md", ["Psychodynamic"])


def test_rejects_reference_outside_project(tmp_path: Path):
    outside = tmp_path.parent / "outside.md"
    outside.write_text(REFERENCE, encoding="utf-8")

    with pytest.raises(ApproachReferenceError, match="inside the project"):
        ApproachReferenceLoader(tmp_path).load("../outside.md", ["CBT"])
