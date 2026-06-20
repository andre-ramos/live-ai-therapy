from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


SECTION_HEADING = re.compile(r"^##\s+\d+\.\s+(.+?)\s*$", re.MULTILINE)
MAX_REFERENCE_BYTES = 512_000


class ApproachReferenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class ApproachReference:
    source: str
    content_hash: str
    markdown: str


class ApproachReferenceLoader:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    def load(self, configured_path: str, selected_approaches: list[str]) -> ApproachReference:
        path = (self.project_root / configured_path).resolve()
        if not path.is_relative_to(self.project_root) or path.suffix.lower() != ".md":
            raise ApproachReferenceError("Approach reference must be a Markdown file inside the project.")
        try:
            if path.stat().st_size > MAX_REFERENCE_BYTES:
                raise ApproachReferenceError("Approach reference exceeds the size limit.")
            raw = path.read_text(encoding="utf-8")
        except ApproachReferenceError:
            raise
        except (OSError, UnicodeError) as error:
            raise ApproachReferenceError("Approach reference could not be read as UTF-8.") from error

        sections = self._sections(raw)
        selected: list[str] = []
        missing: list[str] = []
        for approach in selected_approaches:
            section = self._find_section(approach, sections)
            if section is None:
                missing.append(approach)
            else:
                selected.append(section)
        if missing:
            raise ApproachReferenceError(
                f"Selected approaches are missing from the reference: {', '.join(missing)}."
            )

        markdown = "\n\n---\n\n".join(selected).strip()
        return ApproachReference(
            source=path.relative_to(self.project_root).as_posix(),
            content_hash=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            markdown=markdown,
        )

    @staticmethod
    def _sections(raw: str) -> list[tuple[set[str], str]]:
        matches = list(SECTION_HEADING.finditer(raw))
        sections: list[tuple[set[str], str]] = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
            title = match.group(1)
            alias_text = title.split("—", 1)[0]
            aliases = {
                ApproachReferenceLoader._normalize(alias)
                for alias in alias_text.split("/")
                if alias.strip()
            }
            sections.append((aliases, raw[match.start():end].strip()))
        if not sections:
            raise ApproachReferenceError("Approach reference contains no numbered level-two sections.")
        return sections

    @staticmethod
    def _find_section(approach: str, sections: list[tuple[set[str], str]]) -> str | None:
        requested = ApproachReferenceLoader._normalize(approach)
        for aliases, markdown in sections:
            if requested in aliases:
                return markdown
        return None

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().casefold())
