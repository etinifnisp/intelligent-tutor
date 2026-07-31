"""Lightweight reranker (token overlap + metadata boost)."""

from __future__ import annotations

import re
from typing import Any


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def rerank(query: str, candidates: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
    q_tokens = _tokens(query)
    scored: list[tuple[float, dict[str, Any]]] = []
    for cand in candidates:
        body = cand.get("body") or cand.get("stem_text") or ""
        overlap = len(q_tokens & _tokens(body))
        score = cand.get("rrf_score", 0.0) + overlap * 0.05
        if cand.get("subject_match"):
            score += 0.1
        if cand.get("chapter_match"):
            score += 0.15
        scored.append((score, {**cand, "rerank_score": round(score, 4)}))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]
