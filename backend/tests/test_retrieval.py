"""Regression tests for the persisted hybrid retrieval contract."""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from app.retrieval import indexer, service


def _stable_vectors(texts: list[str], _model_name: str) -> np.ndarray:
    vectors = np.zeros((len(texts), 8), dtype=np.float32)
    for row, text in enumerate(texts):
        for token in text.lower().split():
            vectors[row, int(hashlib.sha256(token.encode()).hexdigest(), 16) % 8] += 1
        norm = np.linalg.norm(vectors[row])
        if norm:
            vectors[row] /= norm
    return vectors


def _configure_index_paths(monkeypatch, tmp_path):
    corpus_path = tmp_path / "corpus.jsonl"
    index_dir = tmp_path / "indexes"
    paths = {
        "CORPUS_V2_PATH": corpus_path,
        "INDEXES_DIR": index_dir,
        "RETRIEVAL_DB_PATH": index_dir / "retrieval.db",
        "FAISS_INDEX_PATH": index_dir / "faiss.index",
        "FAISS_IDS_PATH": index_dir / "faiss_ids.json",
        "RETRIEVAL_MANIFEST_PATH": index_dir / "manifest.json",
        "CONCEPT_NOTES_PATH": index_dir / "concept_notes.jsonl",
    }
    for name, value in paths.items():
        if hasattr(indexer, name):
            monkeypatch.setattr(indexer, name, value)
        if hasattr(service, name):
            monkeypatch.setattr(service, name, value)
    monkeypatch.setattr(indexer, "embedding_metadata", lambda _name: {"backend": "sentence_transformers", "model": "test-model", "vector_dim": 8})
    monkeypatch.setattr(indexer, "embed_texts", _stable_vectors)
    monkeypatch.setattr(service, "embedding_metadata", lambda _name: {"backend": "sentence_transformers", "model": "test-model", "vector_dim": 8})
    monkeypatch.setattr(service, "embed_texts", _stable_vectors)
    monkeypatch.setattr(indexer, "EMBEDDING_MODEL", "test-model")
    monkeypatch.setattr(service, "EMBEDDING_MODEL", "test-model")
    return corpus_path


def _write_corpus(path):
    rows = [
        {"question_id": "physics-1", "subject": "Physics", "chapter": "Motion", "stem_text": "force acceleration newton law", "options": []},
        {"question_id": "math-1", "subject": "Mathematics", "chapter": "Algebra", "stem_text": "quadratic equation roots", "options": []},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return rows


def test_index_load_and_vector_search_are_consistent(monkeypatch, tmp_path):
    corpus_path = _configure_index_paths(monkeypatch, tmp_path)
    rows = _write_corpus(corpus_path)
    indexer.build_indexes()

    retrieval = service.RetrievalService()
    assert retrieval.load()
    assert retrieval._vector_search(indexer.document_text(rows[0]), limit=2)[0] == "physics-1"
    assert retrieval.search("force acceleration", subject="Physics", chapter="Motion")[0]["question_id"] == "physics-1"


def test_load_rejects_stale_corpus_and_fts_input_is_literal(monkeypatch, tmp_path):
    corpus_path = _configure_index_paths(monkeypatch, tmp_path)
    _write_corpus(corpus_path)
    indexer.build_indexes()

    retrieval = service.RetrievalService()
    assert retrieval.load()
    assert service._fts_match_query('(force OR "acceleration")') == '"force" AND "OR" AND "acceleration"'

    with corpus_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"question_id": "changed", "stem_text": "changed"}) + "\n")
    assert not service.RetrievalService().load()


def test_embedding_failure_is_not_replaced_with_process_random_hash(monkeypatch):
    def unavailable(_model_name):
        raise indexer.EmbeddingUnavailableError("dependency unavailable")

    monkeypatch.setattr(indexer, "_load_embedding_model", unavailable)
    with pytest.raises(indexer.EmbeddingUnavailableError):
        indexer.embed_texts(["force acceleration"], "test-model")
