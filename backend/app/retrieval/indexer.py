"""Build validated SQLite FTS5 and FAISS indexes from ``corpus_v2``."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from app.config import (
    CONCEPT_NOTES_PATH,
    CORPUS_V2_PATH,
    EMBEDDING_MODEL,
    FAISS_IDS_PATH,
    FAISS_INDEX_PATH,
    INDEXES_DIR,
    RETRIEVAL_DB_PATH,
    RETRIEVAL_MANIFEST_PATH,
)

logger = logging.getLogger("tutor.retrieval.indexer")
INDEX_SCHEMA_VERSION = 2
EMBEDDING_BACKEND = "sentence_transformers"

# Review priority order for deduplication (higher index = higher priority).
_REVIEW_PRIORITY: dict[str, int] = {
    "NEEDS_REVIEW": 0,
    "AUTO_ACCEPTED": 1,
    "AUTO_VERIFIED": 2,
    "REVIEWED": 3,
}


class EmbeddingUnavailableError(RuntimeError):
    """Raised when the configured embedding model cannot be loaded."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_corpus_v2(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{number}") from exc
            if not row.get("question_id"):
                raise ValueError(f"Missing question_id at {path}:{number}")
            rows.append(row)
    return rows


def _content_hash(question: dict[str, Any]) -> str:
    """Stable content fingerprint for deduplication (text + sorted options)."""
    stem = " ".join((question.get("stem_text") or question.get("normalized_text") or "").split()).lower()
    opts = sorted(
        f"{o.get('label', '').upper()}:{' '.join((o.get('text') or '').split()).lower()}"
        for o in (question.get("options") or [])
        if isinstance(o, dict)
    )
    return hashlib.sha256((stem + "|".join(opts)).encode()).hexdigest()


def deduplicate_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Remove duplicate questions, keeping the highest-reviewed version of each.

    Returns ``(deduped_records, duplicate_count)``.
    """
    best: dict[str, dict[str, Any]] = {}
    for record in records:
        h = _content_hash(record)
        existing = best.get(h)
        if existing is None:
            best[h] = record
            continue
        existing_priority = _REVIEW_PRIORITY.get(str(existing.get("review_status") or ""), 0)
        record_priority = _REVIEW_PRIORITY.get(str(record.get("review_status") or ""), 0)
        if record_priority > existing_priority:
            best[h] = record
    deduped = list(best.values())
    return deduped, len(records) - len(deduped)


def document_text(question: dict[str, Any]) -> str:
    parts = [
        question.get("subject") or "",
        question.get("chapter") or "",
        question.get("topic") or "",
        question.get("stem_text") or question.get("normalized_text") or "",
    ]
    options = question.get("options") or []
    if options:
        parts.append(" ".join(f"{option.get('label', '')}. {option.get('text', '')}" for option in options))
    return "\n".join(part for part in parts if part).strip()


def _load_embedding_model(model_name: str):
    try:
        # Retrieval uses the PyTorch backend. Avoid importing an optional TensorFlow
        # installation, which is unrelated to sentence embedding and can be broken.
        os.environ.setdefault("USE_TF", "0")
        from sentence_transformers import SentenceTransformer

        if getattr(_load_embedding_model, "_model_name", None) != model_name:
            _load_embedding_model._model = SentenceTransformer(model_name)  # type: ignore[attr-defined]
            _load_embedding_model._model_name = model_name  # type: ignore[attr-defined]
        return _load_embedding_model._model  # type: ignore[attr-defined]
    except Exception as exc:
        raise EmbeddingUnavailableError(
            f"Unable to load embedding model {model_name!r}. Reinstall a compatible "
            "sentence-transformers/PyTorch runtime, then rebuild the retrieval index."
        ) from exc


def embedding_metadata(model_name: str = EMBEDDING_MODEL) -> dict[str, Any]:
    model = _load_embedding_model(model_name)
    dimension = int(model.get_sentence_embedding_dimension())
    if dimension <= 0:
        raise EmbeddingUnavailableError(f"Embedding model {model_name!r} reported an invalid dimension.")
    return {"backend": EMBEDDING_BACKEND, "model": model_name, "vector_dim": dimension}


def embed_texts(texts: list[str], model_name: str = EMBEDDING_MODEL) -> np.ndarray:
    if not texts:
        metadata = embedding_metadata(model_name)
        return np.empty((0, metadata["vector_dim"]), dtype=np.float32)
    model = _load_embedding_model(model_name)
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=len(texts) > 500)
    result = np.asarray(vectors, dtype=np.float32)
    if result.ndim != 2 or result.shape[0] != len(texts):
        raise EmbeddingUnavailableError("Embedding model returned an invalid vector batch.")
    return result


def build_fts(conn: sqlite3.Connection, records: list[dict[str, Any]]) -> None:
    conn.execute(
        """
        CREATE VIRTUAL TABLE questions_fts USING fts5(
            question_id UNINDEXED,
            subject UNINDEXED,
            chapter UNINDEXED,
            topic UNINDEXED,
            body,
            tokenize='porter'
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO questions_fts (question_id, subject, chapter, topic, body)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                question["question_id"],
                question.get("subject") or "",
                question.get("chapter") or "",
                question.get("topic") or "",
                document_text(question),
            )
            for question in records
        ],
    )


def build_faiss(vectors: np.ndarray, question_ids: list[str], index_path: Path, ids_path: Path) -> None:
    import faiss

    if vectors.ndim != 2 or vectors.shape[0] != len(question_ids) or vectors.shape[1] <= 0:
        raise ValueError("Vectors and question IDs have incompatible shapes.")
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, str(index_path))
    ids_path.write_text(json.dumps(question_ids), encoding="utf-8")


def _build_note_text(subject: str, chapter: str, bucket: dict[str, Any]) -> str:
    """Produce a structured, data-driven concept note string for LLM consumption."""
    total = bucket["total"]
    topics = ", ".join(sorted(bucket["topics"])[:8]) or "General"
    diff = bucket["difficulty"]
    diff_parts = ", ".join(f"{k} {v}" for k, v in sorted(diff.items()) if v)
    ans_pct = round(100 * bucket["with_answer"] / total) if total else 0
    qtypes = ", ".join(sorted(bucket["qtypes"])[:3]) or "MCQ"
    return (
        f"JEE {subject} · {chapter} ({total} questions). "
        f"Topics: {topics}. "
        f"Difficulty: {diff_parts}. "
        f"Answer key coverage: {ans_pct}%. "
        f"Question types: {qtypes}."
    )


def build_concept_notes(records: list[dict[str, Any]], destination: Path) -> None:
    by_chapter: dict[str, dict[str, Any]] = {}
    for question in records:
        chapter = question.get("chapter") or "General"
        subject = question.get("subject") or "General"
        key = f"{subject}::{chapter}"
        bucket = by_chapter.setdefault(
            key,
            {
                "concept_id": key.replace(" ", "_").lower(),
                "subject": subject,
                "chapter": chapter,
                "sample_question_ids": [],
                "total": 0,
                "with_answer": 0,
                "topics": set(),
                "difficulty": {},
                "qtypes": set(),
            },
        )
        bucket["total"] += 1
        if question.get("correct_answer"):
            bucket["with_answer"] += 1
        if question.get("topic"):
            bucket["topics"].add(question["topic"])
        diff = str(question.get("difficulty") or "Medium").title()
        bucket["difficulty"][diff] = bucket["difficulty"].get(diff, 0) + 1
        qtype = str(question.get("question_type") or "MCQ_SINGLE")
        bucket["qtypes"].add(qtype)
        if len(bucket["sample_question_ids"]) < 3:
            bucket["sample_question_ids"].append(question["question_id"])

    with destination.open("w", encoding="utf-8") as handle:
        for key, bucket in by_chapter.items():
            note_text = _build_note_text(bucket["subject"], bucket["chapter"], bucket)
            record = {
                "concept_id": bucket["concept_id"],
                "subject": bucket["subject"],
                "chapter": bucket["chapter"],
                "sample_question_ids": bucket["sample_question_ids"],
                "total_questions": bucket["total"],
                "answer_coverage_pct": round(100 * bucket["with_answer"] / bucket["total"]) if bucket["total"] else 0,
                "difficulty_distribution": bucket["difficulty"],
                "note": note_text,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _publish(staging_dir: Path, manifest: dict[str, Any]) -> None:
    artifacts = {
        "retrieval.db": RETRIEVAL_DB_PATH,
        "faiss.index": FAISS_INDEX_PATH,
        "faiss_ids.json": FAISS_IDS_PATH,
        "concept_notes.jsonl": CONCEPT_NOTES_PATH,
    }
    INDEXES_DIR.mkdir(parents=True, exist_ok=True)
    for name, destination in artifacts.items():
        os.replace(staging_dir / name, destination)
    staged_manifest = staging_dir / "manifest.json"
    staged_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    os.replace(staged_manifest, RETRIEVAL_MANIFEST_PATH)


def build_indexes(corpus_path: Path | None = None) -> dict[str, Any]:
    corpus_path = corpus_path or CORPUS_V2_PATH
    if not corpus_path.exists():
        raise FileNotFoundError(f"corpus_v2 not found: {corpus_path}")

    raw_records = load_corpus_v2(corpus_path)
    if not raw_records:
        raise ValueError("Corpus must contain at least one uniquely identified question.")

    records, duplicate_count = deduplicate_records(raw_records)
    logger.info(
        "Deduplication: %s raw → %s unique (%s duplicates removed).",
        len(raw_records),
        len(records),
        duplicate_count,
    )

    question_ids = [record["question_id"] for record in records]
    if len(question_ids) != len(set(question_ids)):
        raise ValueError("Corpus contains non-unique question_ids after deduplication.")
    texts = [document_text(record) for record in records]
    if any(not text for text in texts):
        raise ValueError("Corpus contains a question with no indexable text.")

    # Fail before publishing anything when the semantic embedding dependency is unavailable.
    metadata = embedding_metadata(EMBEDDING_MODEL)
    vectors = embed_texts(texts, EMBEDDING_MODEL)
    if vectors.shape[1] != metadata["vector_dim"]:
        raise EmbeddingUnavailableError("Embedding vector dimension changed during index build.")

    INDEXES_DIR.mkdir(parents=True, exist_ok=True)
    staging_dir = INDEXES_DIR / f".build-{uuid.uuid4().hex}"
    staging_dir.mkdir()
    try:
        db_path = staging_dir / "retrieval.db"
        conn = sqlite3.connect(str(db_path))
        try:
            build_fts(conn, records)
            conn.commit()
        finally:
            conn.close()
        build_faiss(vectors, question_ids, staging_dir / "faiss.index", staging_dir / "faiss_ids.json")
        build_concept_notes(records, staging_dir / "concept_notes.jsonl")

        manifest = {
            "schema_version": INDEX_SCHEMA_VERSION,
            "built_at": _utc_now(),
            "corpus_path": str(corpus_path),
            "corpus_sha256": file_sha256(corpus_path),
            "question_count": len(records),
            "question_ids_sha256": hashlib.sha256("\n".join(question_ids).encode()).hexdigest(),
            "embedding_backend": metadata["backend"],
            "embedding_model": metadata["model"],
            "vector_dim": int(vectors.shape[1]),
            "duplicate_stats": {
                "raw_count": len(raw_records),
                "duplicates_removed": duplicate_count,
                "unique_count": len(records),
            },
            "artifacts": {
                name: file_sha256(staging_dir / name)
                for name in ("retrieval.db", "faiss.index", "faiss_ids.json", "concept_notes.jsonl")
            },
        }
        _publish(staging_dir, manifest)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    logger.info("Retrieval indexes built and published for %s questions.", len(records))
    return manifest
