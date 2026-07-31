"""Validated hybrid retrieval: FTS5 + FAISS + RRF + lightweight reranking."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
from collections import OrderedDict
from typing import Any, Optional

from app.config import (
    CONCEPT_NOTES_PATH,
    CORPUS_V2_PATH,
    EMBEDDING_MODEL,
    FAISS_IDS_PATH,
    FAISS_INDEX_PATH,
    RETRIEVAL_CACHE_SIZE,
    RETRIEVAL_DB_PATH,
    RETRIEVAL_MANIFEST_PATH,
)
from app.retrieval.indexer import (
    EMBEDDING_BACKEND,
    INDEX_SCHEMA_VERSION,
    EmbeddingUnavailableError,
    document_text,
    embed_texts,
    embedding_metadata,
    file_sha256,
    load_corpus_v2,
)
from app.retrieval.reranker import rerank

logger = logging.getLogger("tutor.retrieval")
_FTS_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def reciprocal_rank_fusion(rank_lists: list[list[str]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranked in rank_lists:
        for rank, question_id in enumerate(ranked, start=1):
            scores[question_id] = scores.get(question_id, 0.0) + 1.0 / (k + rank)
    return scores


def _ids_digest(question_ids: list[str]) -> str:
    return hashlib.sha256("\n".join(question_ids).encode()).hexdigest()


def _fts_match_query(query: str) -> str:
    """Turn arbitrary user input into literal FTS terms, never FTS syntax."""
    tokens = _FTS_TOKEN_RE.findall(query)
    return " AND ".join(f'"{token}"' for token in tokens)


class RetrievalService:
    def __init__(self) -> None:
        self._corpus: dict[str, dict[str, Any]] = {}
        self._faiss = None
        self._faiss_ids: list[str] = []
        self._concept_notes: dict[str, dict[str, Any]] = {}
        self._cache: OrderedDict[tuple[Any, ...], list[dict[str, Any]]] = OrderedDict()
        self._ready = False

    def _clear(self) -> None:
        self._corpus = {}
        self._faiss = None
        self._faiss_ids = []
        self._concept_notes = {}
        self._cache.clear()
        self._ready = False

    def _load_manifest(self) -> dict[str, Any]:
        if not RETRIEVAL_MANIFEST_PATH.exists():
            raise ValueError("retrieval manifest is missing")
        manifest = json.loads(RETRIEVAL_MANIFEST_PATH.read_text(encoding="utf-8"))
        required = {
            "schema_version",
            "corpus_sha256",
            "question_count",
            "question_ids_sha256",
            "embedding_backend",
            "embedding_model",
            "vector_dim",
            "artifacts",
        }
        missing = required - manifest.keys()
        if missing:
            raise ValueError(f"retrieval manifest is incomplete: {sorted(missing)}")
        return manifest

    def load(self) -> bool:
        self._clear()
        paths = (RETRIEVAL_DB_PATH, FAISS_INDEX_PATH, FAISS_IDS_PATH, CONCEPT_NOTES_PATH, CORPUS_V2_PATH)
        if not all(path.exists() for path in paths):
            logger.warning("Retrieval artifacts are missing; run python -m pipelines.build_retrieval_index")
            return False
        try:
            manifest = self._load_manifest()
            if manifest["schema_version"] != INDEX_SCHEMA_VERSION:
                raise ValueError("retrieval index schema is unsupported")
            if manifest["embedding_backend"] != EMBEDDING_BACKEND or manifest["embedding_model"] != EMBEDDING_MODEL:
                raise ValueError("retrieval index was built with a different embedding configuration")
            if manifest["corpus_sha256"] != file_sha256(CORPUS_V2_PATH):
                raise ValueError("retrieval index is stale for the current corpus")

            artifact_paths = {
                "retrieval.db": RETRIEVAL_DB_PATH,
                "faiss.index": FAISS_INDEX_PATH,
                "faiss_ids.json": FAISS_IDS_PATH,
                "concept_notes.jsonl": CONCEPT_NOTES_PATH,
            }
            if any(manifest["artifacts"].get(name) != file_sha256(path) for name, path in artifact_paths.items()):
                raise ValueError("retrieval artifacts do not match their manifest")

            rows = load_corpus_v2(CORPUS_V2_PATH)
            question_ids = [row["question_id"] for row in rows]
            if len(rows) != manifest["question_count"] or _ids_digest(question_ids) != manifest["question_ids_sha256"]:
                raise ValueError("retrieval corpus metadata does not match its manifest")

            import faiss

            index = faiss.read_index(str(FAISS_INDEX_PATH))
            ids = json.loads(FAISS_IDS_PATH.read_text(encoding="utf-8"))
            metadata = embedding_metadata(EMBEDDING_MODEL)
            if (
                not isinstance(ids, list)
                or index.ntotal != len(ids)
                or index.ntotal != len(rows)
                or index.d != manifest["vector_dim"]
                or index.d != metadata["vector_dim"]
            ):
                raise ValueError("FAISS vectors, IDs, and embedding dimension are incompatible")

            self._corpus = {row["question_id"]: row for row in rows}
            self._faiss = index
            self._faiss_ids = ids
            with CONCEPT_NOTES_PATH.open("r", encoding="utf-8") as handle:
                self._concept_notes = {
                    note["concept_id"]: note
                    for line in handle
                    if line.strip()
                    for note in [json.loads(line)]
                }
            self._ready = True
            logger.info("Retrieval service loaded and validated (%s questions).", len(self._corpus))
            return True
        except (
            EmbeddingUnavailableError,
            ImportError,
            OSError,
            ValueError,
            json.JSONDecodeError,
            sqlite3.Error,
        ) as exc:
            self._clear()
            logger.error("Retrieval service is unavailable: %s", exc, exc_info=True)
            return False

    @property
    def ready(self) -> bool:
        return self._ready

    def lookup_question(self, question_id: str) -> Optional[dict[str, Any]]:
        return self._corpus.get(question_id)

    def all_questions(self) -> list[dict[str, Any]]:
        return list(self._corpus.values())

    def _keyword_search(
        self,
        query: str,
        *,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        limit: int = 20,
    ) -> list[str]:
        match_query = _fts_match_query(query)
        if not match_query:
            return []
        with sqlite3.connect(str(RETRIEVAL_DB_PATH)) as conn:
            sql = "SELECT question_id FROM questions_fts WHERE questions_fts MATCH ?"
            params: list[Any] = [match_query]
            if subject:
                sql += " AND subject = ?"
                params.append(subject)
            if chapter:
                sql += " AND chapter = ?"
                params.append(chapter)
            sql += " LIMIT ?"
            params.append(limit)
            try:
                return [row[0] for row in conn.execute(sql, params).fetchall()]
            except sqlite3.OperationalError as exc:
                logger.warning("FTS query failed for normalized query %r: %s", match_query, exc)
                return []

    def _vector_search(
        self,
        query: str,
        *,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        limit: int = 20,
    ) -> list[str]:
        if self._faiss is None or not query.strip():
            return []
        vectors = embed_texts([query], EMBEDDING_MODEL)
        if vectors.shape[1] != self._faiss.d:
            raise ValueError("Query embedding dimension does not match the FAISS index")
        # Filtering after a small global candidate set drops valid low-frequency chapters.
        candidate_count = self._faiss.ntotal if subject or chapter else min(limit, self._faiss.ntotal)
        _, indices = self._faiss.search(vectors, candidate_count)
        results: list[str] = []
        for idx in indices[0]:
            if idx < 0 or idx >= len(self._faiss_ids):
                continue
            question_id = self._faiss_ids[idx]
            row = self._corpus.get(question_id)
            if not row or (subject and row.get("subject") != subject) or (chapter and row.get("chapter") != chapter):
                continue
            results.append(question_id)
            if len(results) >= limit:
                break
        return results

    def search(
        self,
        query: str,
        *,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        question_id: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if question_id:
            exact = self.lookup_question(question_id)
            if exact:
                return [self._to_evidence(exact, score=1.0, source="exact_id")]
        if not self._ready or not query.strip():
            return []

        cache_key = (query.strip().lower(), subject, chapter, top_k)
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._cache.move_to_end(cache_key)
            return list(cached)
        results = self._search_impl(query, subject=subject, chapter=chapter, top_k=top_k)
        self._cache[cache_key] = results
        self._cache.move_to_end(cache_key)
        while len(self._cache) > RETRIEVAL_CACHE_SIZE:
            self._cache.popitem(last=False)
        return list(results)

    def _search_impl(
        self,
        query: str,
        *,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        keyword_ids = self._keyword_search(query, subject=subject, chapter=chapter, limit=30)
        vector_ids = self._vector_search(query, subject=subject, chapter=chapter, limit=30)
        fused = reciprocal_rank_fusion([keyword_ids, vector_ids])
        candidates: list[dict[str, Any]] = []
        for question_id, score in sorted(fused.items(), key=lambda item: item[1], reverse=True)[:40]:
            row = self._corpus.get(question_id)
            if not row:
                continue
            evidence = self._to_evidence(row, score=score, source="hybrid")
            evidence["subject_match"] = bool(subject and subject == row.get("subject"))
            evidence["chapter_match"] = bool(chapter and chapter == row.get("chapter"))
            evidence["body"] = document_text(row)
            candidates.append(evidence)
        return rerank(query, candidates, top_k=top_k)

    def _to_evidence(self, row: dict[str, Any], score: float, source: str) -> dict[str, Any]:
        return {
            "type": "question",
            "question_id": row["question_id"],
            "subject": row.get("subject"),
            "chapter": row.get("chapter"),
            "topic": row.get("topic"),
            "stem_text": (row.get("stem_text") or "")[:500],
            "review_status": row.get("review_status"),
            "paper_id": row.get("paper_id"),
            "year": row.get("year"),
            "diagram_paths": row.get("diagram_paths") or [],
            "rrf_score": round(score, 4),
            "source": source,
        }

    def concept_note(self, subject: str, chapter: str) -> Optional[dict[str, Any]]:
        key = f"{subject}::{chapter}".replace(" ", "_").lower()
        return self._concept_notes.get(key)

    def format_evidence_block(self, evidence: list[dict[str, Any]]) -> str:
        if not evidence:
            return "No retrieved evidence. Explain uncertainty instead of inventing a citation."
        lines = ["== RETRIEVED EVIDENCE (question-level, not full PDF) =="]
        for position, item in enumerate(evidence, start=1):
            lines.append(
                f"{position}. [{item.get('question_id')}] {item.get('subject')} / {item.get('chapter')}\n"
                f"   {item.get('stem_text', '')[:300]}"
            )
        return "\n".join(lines)
