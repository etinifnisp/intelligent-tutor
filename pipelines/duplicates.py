"""Duplicate detection using normalized stem fingerprints."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any

_STRIP_RE = re.compile(r"[^a-z0-9]+")


def stem_fingerprint(stem_text: str) -> str:
    text = (stem_text or "").lower()
    text = re.sub(r"question\s*:", "", text)
    text = _STRIP_RE.sub("", text)
    text = text[:240]
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def assign_duplicate_groups(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for idx, q in enumerate(questions):
        fp = stem_fingerprint(q.get("stem_text", ""))
        if len(fp) < 8:
            continue
        groups[fp].append(idx)

    for fp, indices in groups.items():
        if len(indices) < 2:
            continue
        group_id = f"dup_{fp[:12]}"
        primary_idx = indices[0]
        for idx in indices:
            questions[idx]["duplicate_group_id"] = group_id
            if idx == primary_idx:
                questions[idx]["duplicate_of"] = None
            else:
                questions[idx]["duplicate_of"] = questions[primary_idx]["question_id"]
                if questions[idx].get("review_status") == "AUTO_VERIFIED":
                    questions[idx]["review_status"] = "DUPLICATE_REVIEW"

    return questions
