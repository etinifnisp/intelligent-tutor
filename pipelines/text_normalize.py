"""Unicode normalization — never overwrites raw extraction."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Deterministic character replacements (from legacy clean_corpus, no LLM).
REPLACEMENTS: dict[str, str] = {
    "−": "-",
    "–": "-",
    "—": "-",
    "×": "x",
    "✘": "x",
    "\u00a0": " ",
}

_WHITESPACE_RE = re.compile(r"[ \t]+")
_NEWLINES_RE = re.compile(r"\n{3,}")


def normalize_unicode(text: str) -> str:
    if not text:
        return ""
    for bad, good in REPLACEMENTS.items():
        text = text.replace(bad, good)
    text = unicodedata.normalize("NFKC", text)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _NEWLINES_RE.sub("\n\n", text)
    return text.strip()


def build_text_layers(raw_text: str) -> dict[str, Any]:
    normalized = normalize_unicode(raw_text)
    return {
        "raw_text": raw_text,
        "normalized_text": normalized,
        "correction_method": "unicode_nfkc",
        "correction_model": None,
        "correction_reason": "phase2_deterministic_normalization",
        "confidence": 1.0,
        "human_review_status": "AUTO",
    }
