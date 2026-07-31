"""Parse legacy raw_text into structured stem, options, and answer."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

OPTION_LINE_RE = re.compile(
    r"^\s*\(?\s*([a-dA-D1-4])\s*\)?\s*[\.\):\-]?\s*(.+)$",
    re.MULTILINE,
)
ANSWER_RE = re.compile(
    r"Answer\s*[:\(]?\s*\(?\s*([a-dA-D1-4])\s*\)?\s*(.*?)$",
    re.IGNORECASE | re.MULTILINE,
)
ANSWER_NUMERIC_RE = re.compile(
    r"Answer\s*[:\(]?\s*\(?\s*([0-9]+(?:\.[0-9]+)?)\s*\)?",
    re.IGNORECASE,
)
QUESTION_PREFIX_RE = re.compile(r"^Question\s*:\s*", re.IGNORECASE)
QUESTION_NUM_PREFIX_RE = re.compile(r"^Q\s*(\d{1,3})\s*:\s*", re.IGNORECASE)
INTERNAL_Q_RE = re.compile(r"\bQ\s*\d{1,3}\s*:")
OPTIONS_HEADER_RE = re.compile(r"^Options\s*:\s*", re.IGNORECASE | re.MULTILINE)
SOLUTION_HEADER_RE = re.compile(r"^Solution\s*:\s*", re.IGNORECASE | re.MULTILINE)
OPTION_FRAGMENT_RE = re.compile(r"^\s*\([a-dA-D]\)\s+")
NUMERIC_ONLY_RE = re.compile(r"^\d+(?:\.\d+)?$")


@dataclass
class ParsedQuestion:
    stem_text: str
    options: list[dict[str, str]] = field(default_factory=list)
    correct_answer: Optional[str] = None
    official_solution: Optional[str] = None
    question_type: str = "MCQ_SINGLE"
    parse_errors: list[str] = field(default_factory=list)


def _normalize_label(label: str) -> str:
    label = label.strip().upper()
    mapping = {"1": "A", "2": "B", "3": "C", "4": "D"}
    return mapping.get(label, label)


def _extract_best_question_block(text: str) -> tuple[str, Optional[int]]:
    """Pick the most likely question block when boundaries are noisy."""
    candidates: list[tuple[int, str, int]] = []

    for m in re.finditer(r"(?:Question\s*:|Q\s*\d{1,3}\s*:)", text, re.IGNORECASE):
        start = m.start()
        chunk = text[start : start + 1200]
        # Trim at next question header if present
        next_m = re.search(
            r"(?:\n\s*Q\s*\d{1,3}\s*:|\n\s*Question\s*:)",
            chunk[m.end() - start :],
            re.IGNORECASE,
        )
        if next_m:
            chunk = chunk[: m.end() - start + next_m.start()]
        qnum = None
        qm = QUESTION_NUM_PREFIX_RE.match(chunk.strip())
        if qm:
            qnum = int(qm.group(1))
        candidates.append((start, chunk.strip(), len(chunk)))

    if not candidates:
        choose = re.search(r"Choose the correct answer", text, re.IGNORECASE)
        if choose:
            return text[choose.start() :].strip(), None
        return text, None

    # Prefer last Question:/Qn: block — often the true boundary in noisy extractions
    candidates.sort(key=lambda x: x[0])
    _, best, _ = candidates[-1]
    qnum = None
    qm = QUESTION_NUM_PREFIX_RE.match(best)
    if qm:
        qnum = int(qm.group(1))
    return best, qnum


def _stem_looks_corrupt(stem: str) -> bool:
    if not stem:
        return True
    stripped = stem.strip()
    if len(stripped) < 12:
        return True
    if NUMERIC_ONLY_RE.match(stripped):
        return True
    if re.match(r"^\([A-Da-d]\)\s*$", stripped):
        return True
    if OPTION_FRAGMENT_RE.match(stem):
        return True
    if INTERNAL_Q_RE.search(stem):
        return True
    return False


def _apply_repair(
    working_text: str,
    errors: list[str],
) -> tuple[str, str, str, str, Optional[int]]:
    repaired, qnum = _extract_best_question_block(working_text)
    if not repaired:
        return "", "", "", "", qnum
    q_part, o_part, a_part, s_part = _split_sections(repaired)
    q_part = QUESTION_PREFIX_RE.sub("", q_part).strip()
    qm = QUESTION_NUM_PREFIX_RE.match(q_part)
    if qm:
        qnum = int(qm.group(1))
        q_part = QUESTION_NUM_PREFIX_RE.sub("", q_part).strip()
    if repaired != working_text:
        errors.append("boundary_repaired")
    return q_part, o_part, a_part, s_part, qnum


def _split_sections(text: str) -> tuple[str, str, str, str]:
    """Return (question_part, options_part, answer_part, solution_part)."""
    answer_part = ""
    solution_part = ""
    working = text

    sol_match = SOLUTION_HEADER_RE.search(working)
    if sol_match:
        solution_part = working[sol_match.end() :].strip()
        working = working[: sol_match.start()].strip()

    answer_match = None
    for m in ANSWER_RE.finditer(working):
        answer_match = m
    if not answer_match:
        for m in ANSWER_NUMERIC_RE.finditer(working):
            answer_match = m

    if answer_match:
        answer_part = answer_match.group(0)
        working = working[: answer_match.start()].strip()

    options_match = OPTIONS_HEADER_RE.search(working)
    if options_match:
        question_part = working[: options_match.start()].strip()
        options_part = working[options_match.end() :].strip()
    else:
        question_part = working
        options_part = ""

    return question_part, options_part, answer_part, solution_part


def _parse_options_block(options_part: str) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    if not options_part:
        return options

    current_label: Optional[str] = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_label, current_lines
        if current_label and current_lines:
            options.append(
                {
                    "label": current_label,
                    "text": " ".join(line.strip() for line in current_lines if line.strip()),
                }
            )
        current_label = None
        current_lines = []

    for line in options_part.splitlines():
        m = OPTION_LINE_RE.match(line)
        if m:
            flush()
            current_label = _normalize_label(m.group(1))
            rest = m.group(2).strip()
            if rest:
                current_lines.append(rest)
        elif current_label:
            if line.strip():
                current_lines.append(line.strip())

    flush()
    return options


def _parse_inline_options(question_part: str) -> tuple[str, list[dict[str, str]]]:
    """Handle texts where options appear without an Options: header."""
    options: list[dict[str, str]] = []
    lines = question_part.splitlines()
    stem_lines: list[str] = []
    current_label: Optional[str] = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_label, current_lines
        if current_label and current_lines:
            options.append(
                {
                    "label": current_label,
                    "text": " ".join(current_lines),
                }
            )
        current_label = None
        current_lines = []

    for line in lines:
        m = OPTION_LINE_RE.match(line)
        if m and not stem_lines:
            # options before stem — unusual, keep as stem
            stem_lines.append(line)
        elif m:
            flush()
            current_label = _normalize_label(m.group(1))
            rest = m.group(2).strip()
            if rest:
                current_lines.append(rest)
        elif current_label:
            if line.strip():
                current_lines.append(line.strip())
        else:
            stem_lines.append(line)

    flush()
    if options:
        question_part = "\n".join(stem_lines).strip()
    return question_part, options


def parse_raw_text(text: str, declared_type: str = "MCQ-single") -> ParsedQuestion:
    errors: list[str] = []
    question_number_in_paper: Optional[int] = None

    working_text = text
    question_part, options_part, answer_part, solution_part = _split_sections(working_text)

    question_part = QUESTION_PREFIX_RE.sub("", question_part).strip()
    qm = QUESTION_NUM_PREFIX_RE.match(question_part)
    if qm:
        question_number_in_paper = int(qm.group(1))
        question_part = QUESTION_NUM_PREFIX_RE.sub("", question_part).strip()

    if _stem_looks_corrupt(question_part):
        question_part, options_part, answer_part, solution_part, qnum = _apply_repair(
            working_text, errors
        )
        if qnum:
            question_number_in_paper = qnum

    options = _parse_options_block(options_part)

    if not options:
        question_part, inline_options = _parse_inline_options(question_part)
        options = inline_options

    if _stem_looks_corrupt(question_part):
        question_part, options_part, answer_part, solution_part, qnum = _apply_repair(
            working_text, errors
        )
        if qnum:
            question_number_in_paper = qnum
        options = _parse_options_block(options_part)
        if not options and "Choose the correct" not in question_part:
            question_part, inline_options = _parse_inline_options(question_part)
            if _stem_looks_corrupt(question_part):
                # Keep options only if stem still valid after inline parse
                options = []
            else:
                options = inline_options

    correct_answer: Optional[str] = None
    if answer_part:
        m = ANSWER_RE.search(answer_part)
        if m:
            correct_answer = _normalize_label(m.group(1))
        else:
            m_num = ANSWER_NUMERIC_RE.search(answer_part)
            if m_num:
                correct_answer = m_num.group(1)

    qtype = "MCQ_SINGLE"
    declared = (declared_type or "").lower()
    if declared == "integer" or "integer answer" in text.lower() or "nearest integer" in text.lower():
        qtype = "INTEGER"
    elif len(options) == 0 and correct_answer and correct_answer.isdigit():
        qtype = "INTEGER"
    elif len(options) > 1:
        qtype = "MCQ_SINGLE"

    if not question_part:
        errors.append("empty_stem")
    if qtype == "MCQ_SINGLE" and len(options) < 2:
        errors.append("insufficient_options")
    if not correct_answer:
        errors.append("missing_answer_key")

    return ParsedQuestion(
        stem_text=question_part,
        options=options,
        correct_answer=correct_answer,
        official_solution=solution_part or None,
        question_type=qtype,
        parse_errors=errors,
    )


# Expose for pipeline enrichment
def extract_question_number_in_paper(text: str) -> Optional[int]:
    _, qnum = _extract_best_question_block(text)
    return qnum
