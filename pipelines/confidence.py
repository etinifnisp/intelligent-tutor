"""Confidence scoring and review-status assignment."""

from __future__ import annotations

from typing import Any

from pipelines.question_parser import ParsedQuestion


def score_extraction(parsed: ParsedQuestion, has_pdf_match: bool, has_diagrams: bool) -> float:
    score = 0.35
    stem = parsed.stem_text or ""
    if len(stem) >= 40:
        score += 0.15
    elif len(stem) >= 15:
        score += 0.08
    else:
        score -= 0.1

    if parsed.correct_answer:
        score += 0.2
    if parsed.question_type == "INTEGER":
        if parsed.correct_answer:
            score += 0.1
    elif len(parsed.options) >= 4:
        score += 0.2
    elif len(parsed.options) >= 2:
        score += 0.1

    if not parsed.parse_errors:
        score += 0.1
    else:
        score -= 0.05 * len(parsed.parse_errors)

    if has_pdf_match:
        score += 0.1
    if has_diagrams:
        score += 0.05

    return round(max(0.0, min(1.0, score)), 3)


def score_classification(chapter: str, topic: str, subject: str) -> float:
    score = 0.5
    if subject in {"Physics", "Chemistry", "Mathematics"}:
        score += 0.2
    if chapter and chapter not in {"General", "Unknown", ""}:
        score += 0.15
    if topic and topic == chapter:
        score += 0.05
    return round(min(1.0, score), 3)


def score_answer_key(parsed: ParsedQuestion) -> float:
    if parsed.correct_answer:
        if parsed.question_type == "MCQ_SINGLE" and parsed.correct_answer in {"A", "B", "C", "D"}:
            return 1.0
        if parsed.question_type == "INTEGER":
            return 0.9
        return 0.75
    return 0.0


def assign_review_status(
    extraction_confidence: float,
    answer_key_confidence: float,
    parse_errors: list[str],
    is_duplicate: bool,
) -> str:
    if is_duplicate:
        return "DUPLICATE_REVIEW"
    if parse_errors and "empty_stem" in parse_errors:
        return "NEEDS_REVIEW"
    if extraction_confidence >= 0.85 and answer_key_confidence >= 0.9 and not parse_errors:
        return "AUTO_VERIFIED"
    if extraction_confidence >= 0.65 and answer_key_confidence >= 0.75:
        return "AUTO_ACCEPTED"
    return "NEEDS_REVIEW"


def needs_review_queue(
    question: dict[str, Any],
) -> bool:
    return question.get("review_status") in {
        "NEEDS_REVIEW",
        "DUPLICATE_REVIEW",
    } or question.get("extraction_confidence", 1) < 0.6
