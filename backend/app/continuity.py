from __future__ import annotations

import json
import re
import unicodedata
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import LongitudinalProfile, LongitudinalRecord, SessionSummary, TherapySession

RECORD_TYPES = {"topic", "entity", "chronology", "pattern", "goal"}
RECORD_STATUSES = {"active", "deferred", "resolved"}


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(
        "".join(character for character in normalized if not unicodedata.combining(character)).split()
    )


def generated_text_matches_language(text: str, language: str) -> bool:
    """Reject clearly wrong-language output while accepting names and short neutral fragments."""
    normalized = f" {normalize_text(text)} "
    markers = {
        "pt-BR": (" que ", " de ", " para ", " com ", " uma ", " pessoa ", " sessao ", " sentiu "),
        "en-US": (" the ", " and ", " with ", " for ", " person ", " session ", " felt ", " discussed "),
    }
    other = "en-US" if language == "pt-BR" else "pt-BR"
    expected_score = sum(marker in normalized for marker in markers.get(language, ()))
    other_score = sum(marker in normalized for marker in markers.get(other, ()))
    return not (other_score >= 2 and other_score > expected_score)


def parse_json_object(raw: str) -> dict[str, Any]:
    cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def payload_matches_language(payload: dict[str, Any], language: str) -> bool:
    values: list[str] = []
    for key in ("summary", "narrative"):
        if isinstance(payload.get(key), str):
            values.append(payload[key])
    for collection in ("memories", "topics", "entities", "chronology", "patterns", "goals"):
        for item in payload.get(collection, []) if isinstance(payload.get(collection, []), list) else []:
            if isinstance(item, dict):
                values.extend(str(item.get(key, "")) for key in ("title", "content", "follow_up_question"))
    return generated_text_matches_language(" ".join(values), language)


def recent_eligible_sessions(db: Session, language: str, limit: int) -> list[TherapySession]:
    return list(db.scalars(
        select(TherapySession)
        .where(
            TherapySession.language == language,
            TherapySession.continuity_eligible.is_(True),
            TherapySession.status == "ended",
        )
        .order_by(TherapySession.ended_at.desc(), TherapySession.started_at.desc())
        .limit(limit)
    ).all())


def build_continuity_snapshot(db: Session, language: str, recent_count: int) -> dict[str, Any]:
    profile = db.scalar(select(LongitudinalProfile).where(LongitudinalProfile.language == language))
    sessions = recent_eligible_sessions(db, language, recent_count)
    session_ids = [item.id for item in sessions]
    summaries = []
    if session_ids:
        rows = db.scalars(
            select(SessionSummary).where(
                SessionSummary.session_id.in_(session_ids),
                SessionSummary.language == language,
            )
        ).all()
        by_session = {item.session_id: item.summary for item in rows}
        summaries = [
            {"session_id": item.id, "ended_at": item.ended_at.isoformat() if item.ended_at else None,
             "summary": by_session[item.id]}
            for item in reversed(sessions) if item.id in by_session
        ]
    records = []
    if session_ids:
        rows = db.scalars(
            select(LongitudinalRecord)
            .where(
                LongitudinalRecord.language == language,
                LongitudinalRecord.source_session_id.in_(session_ids),
                LongitudinalRecord.status != "resolved",
            )
            .order_by(LongitudinalRecord.importance.desc(), LongitudinalRecord.created_at.desc())
            .limit(20)
        ).all()
        records = [record_as_dict(item) for item in rows]
    return {
        "language": language,
        "longitudinal_narrative": profile.narrative if profile else "",
        "recent_session_ids": session_ids,
        "recent_summaries": summaries,
        "active_records": records,
    }


def record_as_dict(record: LongitudinalRecord) -> dict[str, Any]:
    return {
        "record_type": record.record_type,
        "title": record.title,
        "content": record.content,
        "status": record.status,
        "confidence": record.confidence,
        "importance": record.importance,
        "follow_up_question": record.follow_up_question,
        "source_session_id": record.source_session_id,
    }


def should_search_archive(
    db: Session,
    text: str,
    language: str,
    recent_session_ids: list[str],
    trigger_phrases: list[str],
) -> bool:
    normalized = normalize_text(text)
    if any(normalize_text(phrase) in normalized for phrase in trigger_phrases):
        return True
    statement = select(LongitudinalRecord).where(LongitudinalRecord.language == language)
    if recent_session_ids:
        statement = statement.where(LongitudinalRecord.source_session_id.not_in(recent_session_ids))
    candidates = db.scalars(statement.order_by(LongitudinalRecord.importance.desc()).limit(200)).all()
    meaningful_words = set(re.findall(r"\b[\w-]{4,}\b", normalized))
    for item in candidates:
        title_words = set(re.findall(r"\b[\w-]{4,}\b", normalize_text(item.title)))
        if title_words and title_words <= meaningful_words:
            return True
        if item.record_type == "entity" and normalize_text(item.title) in normalized:
            return True
    return False


def persist_longitudinal_records(
    db: Session, session_id: str, language: str, payload: dict[str, Any]
) -> list[LongitudinalRecord]:
    db.query(LongitudinalRecord).filter(LongitudinalRecord.source_session_id == session_id).delete()
    created: list[LongitudinalRecord] = []
    collections = {
        "topics": "topic", "entities": "entity", "chronology": "chronology",
        "patterns": "pattern", "goals": "goal",
    }
    for collection, record_type in collections.items():
        values = payload.get(collection, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()[:255]
            content = str(item.get("content", "")).strip()
            if not title or not content:
                continue
            status = str(item.get("status", "active"))
            record = LongitudinalRecord(
                id=f"continuity_{uuid.uuid4().hex}",
                record_type=record_type,
                title=title,
                content=content,
                status=status if status in RECORD_STATUSES else "active",
                confidence=_score(item.get("confidence", 0.5)),
                importance=_score(item.get("importance", 0.5)),
                follow_up_question=str(item.get("follow_up_question", "")).strip() or None,
                source_session_id=session_id,
                source_message_ids=json.dumps(item.get("source_message_ids", [])),
                language=language,
            )
            db.add(record)
            created.append(record)
    return created


def _score(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def compact_structured_context(records: list[LongitudinalRecord]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {kind: [] for kind in RECORD_TYPES}
    for item in records:
        result[item.record_type].append(record_as_dict(item))
    return result
