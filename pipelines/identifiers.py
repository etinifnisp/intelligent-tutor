"""Stable IDs for papers and questions."""

from __future__ import annotations

import re


def slugify(value: str) -> str:
    value = value.replace(".pdf", "")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def paper_id_from_filename(paper_filename: str) -> str:
    return slugify(paper_filename or "unknown_paper")


def question_id_from_parts(paper_filename: str, legacy_number: int | str) -> str:
    return f"{paper_id_from_filename(paper_filename)}_q{legacy_number}"


def normalize_difficulty(value: str) -> str:
    mapping = {
        "easy": "EASY",
        "medium": "MEDIUM",
        "hard": "HARD",
    }
    return mapping.get((value or "").lower(), "MEDIUM")


def normalize_exam_type(value: str) -> str:
    v = (value or "").upper()
    if "ADVANCED" in v:
        return "JEE_ADVANCED"
    return "JEE_MAIN"
