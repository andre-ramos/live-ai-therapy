from datetime import timedelta

from backend.app.continuity import (
    build_continuity_snapshot,
    generated_text_matches_language,
    should_search_archive,
)
from backend.app.db import (
    Base, Database, LongitudinalProfile, LongitudinalRecord, SessionSummary,
    TherapySession, utc_now,
)
from backend.app.memory import VectorMemory


def make_db():
    database = Database("sqlite:///:memory:")
    Base.metadata.create_all(database.engine)
    return database.session_factory()


def add_ended_session(db, session_id: str, language: str, days_ago: int, eligible: bool = True):
    ended_at = utc_now() - timedelta(days=days_ago)
    session = TherapySession(
        id=session_id,
        language=language,
        psychologist_name="Sandy",
        selected_approaches="[]",
        status="ended",
        ended_at=ended_at,
        continuity_eligible=eligible,
    )
    db.add(session)
    db.add(SessionSummary(
        session_id=session_id,
        summary=f"Summary for {session_id}",
        language=language,
    ))
    return session


def test_snapshot_uses_only_recent_eligible_matching_language_sessions():
    db = make_db()
    for index in range(7):
        add_ended_session(db, f"pt-{index}", "pt-BR", index)
    add_ended_session(db, "en-0", "en-US", 0)
    add_ended_session(db, "legacy", "pt-BR", 0, eligible=False)
    db.add(LongitudinalProfile(language="pt-BR", narrative="História longitudinal."))
    db.commit()

    snapshot = build_continuity_snapshot(db, "pt-BR", 5)

    assert snapshot["language"] == "pt-BR"
    assert snapshot["longitudinal_narrative"] == "História longitudinal."
    assert snapshot["recent_session_ids"] == ["pt-0", "pt-1", "pt-2", "pt-3", "pt-4"]
    assert "en-0" not in snapshot["recent_session_ids"]
    assert "legacy" not in snapshot["recent_session_ids"]


def test_old_archive_trigger_supports_explicit_phrases_and_known_entities():
    db = make_db()
    add_ended_session(db, "old", "pt-BR", 20)
    db.add(LongitudinalRecord(
        id="record-1",
        record_type="entity",
        title="Marina",
        content="Colega mencionada em um conflito anterior.",
        source_session_id="old",
        language="pt-BR",
    ))
    db.commit()

    assert should_search_archive(db, "Você lembra do que aconteceu?", "pt-BR", [], ["lembra"])
    assert should_search_archive(db, "A Marina voltou a falar comigo.", "pt-BR", [], ["lembra"])
    assert not should_search_archive(db, "Hoje eu acordei cansado.", "pt-BR", [], ["lembra"])
    assert not should_search_archive(db, "Marina spoke to me.", "en-US", [], ["remember"])


def test_generated_memory_language_validation_rejects_clear_mismatch():
    assert generated_text_matches_language(
        "A pessoa falou sobre a sessão e sobre o que sentiu com a família.", "pt-BR"
    )
    assert not generated_text_matches_language(
        "The person discussed the session and what they felt with the family.", "pt-BR"
    )
    assert generated_text_matches_language(
        "The person discussed the session and what they felt with the family.", "en-US"
    )


def test_archive_search_is_language_scoped_and_excludes_recent_sessions(tmp_path):
    class Embeddings:
        def embed(self, _texts):
            return [[0.1, 0.2]]

    class Collection:
        def __init__(self):
            self.where = None

        def count(self):
            return 20

        def query(self, **kwargs):
            self.where = kwargs["where"]
            return {
                "documents": [["Um tópico de dez sessões atrás."]],
                "metadatas": [[{"session_id": "session-old", "language": "pt-BR"}]],
                "distances": [[0.1]],
            }

    memory = VectorMemory(str(tmp_path), Embeddings())
    memory.collection = Collection()

    results = memory.search_archive(
        "Isso aconteceu novamente",
        "pt-BR",
        ["session_summary", "longitudinal_record"],
        [f"recent-{index}" for index in range(5)],
        3,
        0.72,
    )

    assert results[0]["metadata"]["session_id"] == "session-old"
    filters = memory.collection.where["$and"]
    assert {"language": "pt-BR"} in filters
    assert {"continuity_eligible": True} in filters
    assert {"session_id": {"$nin": [f"recent-{index}" for index in range(5)]}} in filters
