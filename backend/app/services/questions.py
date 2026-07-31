"""Single question-source boundary for legacy corpus and retrieval records."""

from __future__ import annotations

import re
from typing import Any


_OPTIONS_HEADER_RE = re.compile(r"\n\s*Options?\s*:\s*", re.IGNORECASE)
_ANSWER_HEADER_RE = re.compile(r"\n\s*(?:Answer|Ans\.?)\s*:?[\s\S]*$", re.IGNORECASE)
_OPTION_LINE_RE = re.compile(
    r"^\s*(?:\(([a-dA-D1-4])\)|\[([a-dA-D1-4])\]|([a-dA-D1-4])[\).:])\s*(.*)$"
)
_ANSWER_VALUE_RE = re.compile(
    r"(?:Answer|Ans\.?)\s*:?[\s]*(?:\(([a-dA-D1-4])\)|\[([a-dA-D1-4])\]|([a-dA-D1-4]))",
    re.IGNORECASE,
)
_CHOICE_LABELS = ("A", "B", "C", "D")


def _normalise_choice_label(value: str) -> str:
    value = value.strip().upper()
    return {"1": "A", "2": "B", "3": "C", "4": "D"}.get(value, value)


def _structured_choices(question: dict[str, Any]) -> list[dict[str, str]]:
    choices: dict[str, str] = {}
    for option in question.get("options") or []:
        if not isinstance(option, dict):
            continue
        label = _normalise_choice_label(str(option.get("label") or ""))
        text = " ".join(str(option.get("text") or "").split())
        if label in _CHOICE_LABELS and text and label not in choices:
            choices[label] = text
    if tuple(choices) != _CHOICE_LABELS:
        return []
    return [{"label": label, "text": choices[label]} for label in _CHOICE_LABELS]


def _choices_from_raw(raw_text: str) -> list[dict[str, str]]:
    header = _OPTIONS_HEADER_RE.search(raw_text)
    if not header:
        return []
    block = _ANSWER_HEADER_RE.sub("", raw_text[header.end() :]).strip()
    choices: dict[str, str] = {}
    current_label = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_label, current_lines
        text = " ".join(" ".join(current_lines).split())
        if current_label in _CHOICE_LABELS and text and current_label not in choices:
            choices[current_label] = text
        current_label = ""
        current_lines = []

    for line in block.splitlines():
        match = _OPTION_LINE_RE.match(line)
        if match:
            flush()
            current_label = _normalise_choice_label(next(v for v in match.groups()[:3] if v))
            if match.group(4).strip():
                current_lines.append(match.group(4).strip())
        elif current_label and line.strip():
            current_lines.append(line.strip())
    flush()

    if tuple(choices) != _CHOICE_LABELS:
        return []
    return [{"label": label, "text": choices[label]} for label in _CHOICE_LABELS]


def prepare_practice_question(question: dict[str, Any]) -> dict[str, Any] | None:
    """Return a clean, source-labelled four-choice PYQ or reject an unsafe record."""
    year = question.get("year")
    exam_type = str(question.get("exam_type") or "").strip()
    if not year or not exam_type:
        return None

    choices = _structured_choices(question)
    raw_text = str(question.get("raw_text") or "")
    if not choices:
        choices = _choices_from_raw(raw_text)
    if len(choices) != 4:
        return None

    stem = str(question.get("stem_text") or "").strip()
    if not stem and raw_text:
        options_header = _OPTIONS_HEADER_RE.search(raw_text)
        stem = raw_text[: options_header.start()] if options_header else raw_text
    stem = re.sub(r"^\s*(?:Question\s*:|Q\.?\s*\d+\s*[:.)-]?)\s*", "", stem, flags=re.IGNORECASE)
    stem = "\n".join(line.strip() for line in stem.splitlines() if line.strip()).strip()
    if len(stem) < 12:
        return None

    correct_answer = str(question.get("correct_answer") or "").strip()
    if not correct_answer and raw_text:
        answer_match = _ANSWER_VALUE_RE.search(raw_text)
        if answer_match:
            correct_answer = next(v for v in answer_match.groups() if v)
    correct_answer = _normalise_choice_label(correct_answer) if correct_answer else None

    question_number = question.get("question_number") or question.get("legacy_question_number")
    question_id = question.get("question_id") or (
        f"q_{question_number}" if question_number is not None else None
    )
    if not question_id:
        return None

    difficulty = str(question.get("difficulty") or "Medium").title()
    return {
        "question_id": str(question_id),
        "question_number": question_number,
        "paper_filename": question.get("paper_filename"),
        "year": int(year),
        "exam_type": exam_type,
        "session": question.get("session"),
        "shift": question.get("shift"),
        "subject": question.get("subject"),
        "chapter": question.get("chapter"),
        "topic": question.get("topic"),
        "difficulty": difficulty,
        "question_type": "MCQ_SINGLE",
        "marks_positive": question.get("marks_positive", 4),
        "marks_negative": question.get("marks_negative", -1),
        "stem_text": stem,
        "options": choices,
        "correct_answer": correct_answer,
        "official_solution": question.get("official_solution"),
        "images": list(question.get("images") or []),
        "diagram_paths": list(question.get("diagram_paths") or []),
        "source": {
            "kind": "PYQ",
            "exam": exam_type,
            "year": int(year),
            "session": question.get("session"),
            "shift": question.get("shift"),
        },
    }


def practice_question_pool(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [prepared for question in questions if (prepared := prepare_practice_question(question))]


def build_question_lookup(questions_ram: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for question in questions_ram:
        for key in (
            question.get("question_id"),
            question.get("id"),
            f"q_{question['question_number']}" if question.get("question_number") is not None else None,
        ):
            if key:
                lookup.setdefault(str(key), question)
    return lookup


def merge_question_sources(primary: dict[str, Any], secondary: dict[str, Any] | None) -> dict[str, Any]:
    """Keep the canonical retrieval record while preserving richer legacy text/images."""
    if not secondary:
        return primary
    merged = dict(primary)
    primary_text = primary.get("stem_text") or primary.get("raw_text") or ""
    secondary_text = secondary.get("raw_text") or ""
    if secondary_text and (
        not primary_text
        or (";" in primary_text and "[symbol]" not in primary_text)
        or len(secondary_text) > len(primary_text) * 1.15
        or ("Options:" in secondary_text and "Options:" not in primary_text)
    ):
        merged["raw_text"] = secondary_text
    if secondary.get("images"):
        merged["images"] = secondary["images"]
    if not merged.get("correct_answer") and secondary.get("correct_answer"):
        merged["correct_answer"] = secondary["correct_answer"]
    return merged


def resolve_question(
    question_id: str | None,
    questions_ram: list[dict[str, Any]],
    retrieval: Any,
    lookup: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if not question_id:
        return None
    lookup = lookup or build_question_lookup(questions_ram)
    if question := lookup.get(question_id):
        return question
    if not getattr(retrieval, "ready", False):
        return None
    if question := retrieval.lookup_question(question_id):
        legacy = question.get("legacy_question_number")
        return merge_question_sources(question, lookup.get(f"q_{legacy}") if legacy is not None else None)
    if question_id.startswith("q_"):
        try:
            legacy_number = int(question_id[2:])
        except ValueError:
            return None
        for question in retrieval.all_questions():
            if question.get("legacy_question_number") == legacy_number:
                return merge_question_sources(question, lookup.get(question_id))
    return None


def question_pool(questions_ram: list[dict[str, Any]], retrieval: Any) -> list[dict[str, Any]]:
    return retrieval.all_questions() if getattr(retrieval, "ready", False) else questions_ram
