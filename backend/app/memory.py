from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .providers import EmbeddingProvider

logger = logging.getLogger(__name__)


class VectorMemory:
    def __init__(self, path: str, embedding_provider: EmbeddingProvider):
        self.path = Path(path)
        self.embedding_provider = embedding_provider
        self.collection: Any = None

    def initialize(self) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        import chromadb

        client = chromadb.PersistentClient(path=str(self.path))
        self.collection = client.get_or_create_collection(
            name="memories",
            metadata={"hnsw:space": "cosine", "embedding_model": "text-embedding-3-small"},
        )

    @property
    def ready(self) -> bool:
        return self.collection is not None

    def add(self, memory_id: str, text: str, metadata: dict[str, Any]) -> None:
        if not self.collection:
            raise RuntimeError("Vector memory is unavailable")
        embedding = self.embedding_provider.embed([text])[0]
        self.collection.upsert(ids=[memory_id], documents=[text], embeddings=[embedding], metadatas=[metadata])

    def search(self, query: str, language: str, top_k: int, threshold: float) -> list[dict[str, Any]]:
        return self._search(query, language, top_k, threshold)

    def search_archive(
        self,
        query: str,
        language: str,
        source_types: list[str],
        excluded_session_ids: list[str],
        top_k: int,
        threshold: float,
    ) -> list[dict[str, Any]]:
        return self._search(
            query,
            language,
            top_k,
            threshold,
            source_types=source_types,
            excluded_session_ids=set(excluded_session_ids),
        )

    def _search(
        self,
        query: str,
        language: str,
        top_k: int,
        threshold: float,
        source_types: list[str] | None = None,
        excluded_session_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.collection or self.collection.count() == 0:
            return []
        embedding = self.embedding_provider.embed([query])[0]
        filters: list[dict[str, Any]] = [{"language": language}]
        if source_types:
            filters.extend([
                {"continuity_eligible": True},
                {"source": {"$in": source_types}},
            ])
        if excluded_session_ids:
            filters.append({"session_id": {"$nin": sorted(excluded_session_ids)}})
        where = filters[0] if len(filters) == 1 else {"$and": filters}
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(self.collection.count(), top_k),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        memories: list[dict[str, Any]] = []
        for index, document in enumerate(result.get("documents", [[]])[0]):
            metadata = result.get("metadatas", [[]])[0][index]
            if metadata.get("session_id") in (excluded_session_ids or set()):
                continue
            distance = result.get("distances", [[]])[0][index]
            score = 1 - float(distance)
            if score >= threshold:
                memories.append({
                    "content": document,
                    "metadata": metadata,
                    "score": score,
                })
            if len(memories) >= top_k:
                break
        return memories

    def delete(self, memory_id: str) -> None:
        if self.collection:
            self.collection.delete(ids=[memory_id])

    def delete_session(self, session_id: str) -> None:
        if self.collection:
            self.collection.delete(where={"session_id": session_id})
