"""Unified answer checking — MCQ, numeric, official-key comparison."""

from __future__ import annotations

import re
from typing import Any, Optional

from app.verification.chemistry_verifier import verify_numeric_answer as chem_verify_numeric
from app.verification.math_verifier import extract_numbers, match_mcq_option, verify_numeric_submission
from app.verification.physics_verifier import match_option as physics_match_option
from app.verification.schemas import ToolCallRecord, VerificationReport, VerificationStatus

_OPTION_RE = re.compile(r"\boption\s+([a-d])\b", re.I)
_ANSWER_IN_TEXT_RE = re.compile(
    r"(?:answer\s*(?:is|:)\s*)([A-D]|\d+(?:\.\d+)?(?:\s*[x×]\s*10\s*-?\d+)?)",
    re.I,
)


def extract_submitted_option(message: str) -> Optional[str]:
    text = message.strip()
    m = _OPTION_RE.search(text)
    if m:
        return m.group(1).upper()
    if len(text) == 1 and text.upper() in "ABCD":
        return text.upper()
    if "option" in text.lower():
        m2 = re.search(r"\b([a-d])\b", text, re.I)
        if m2:
            return m2.group(1).upper()
    return None


_NUMERIC_ANSWER_RE = re.compile(
    r"answer\s*(?:is|:)\s*(-?\d+(?:\.\d+)?(?:\s*(?:[x×]\s*10\s*-?\d+|[a-zA-Z][a-zA-Z\s-]*)?)?)",
    re.I,
)


def get_official_answer(question: dict[str, Any]) -> Optional[str]:
    ans = question.get("correct_answer") or question.get("answer")
    qt = str(question.get("question_type") or "").upper()
    is_integer = "INTEGER" in qt or question.get("category") == "integer"

    raw = question.get("raw_text") or ""
    layers = question.get("text_layers") or {}
    raw = layers.get("raw_text") or raw

    if is_integer and (not ans or str(ans).strip().upper() in "ABCD"):
        m = _NUMERIC_ANSWER_RE.search(raw)
        if m:
            return m.group(1).strip()

    if ans is not None and str(ans).strip():
        return str(ans).strip()

    m = _ANSWER_IN_TEXT_RE.search(raw)
    if m:
        return m.group(1).strip()
    return None


def _question_type(question: dict[str, Any]) -> str:
    return str(question.get("question_type") or "").upper()


def _is_numeric_type(question: dict[str, Any]) -> bool:
    qt = _question_type(question)
    return "INTEGER" in qt or "NUMERIC" in qt or question.get("category") == "integer"


def verify_student_answer(message: str, question: Optional[dict[str, Any]]) -> VerificationReport:
    """Deterministic student-answer verification."""
    if not question:
        return VerificationReport(
            status=VerificationStatus.UNVERIFIED,
            confidence=0.0,
            summary="No question context for verification.",
        )

    official = get_official_answer(question)
    subject = (question.get("subject") or "").lower()
    tool_calls: list[ToolCallRecord] = []
    checks_passed: list[str] = []
    checks_failed: list[str] = []

    try:
        if _is_numeric_type(question) and official:
            nums_in_official = extract_numbers(str(official))
            if not nums_in_official and official.upper() in "ABCD":
                return VerificationReport(
                    status=VerificationStatus.UNVERIFIED,
                    confidence=0.2,
                    summary="Integer question has non-numeric answer key.",
                    official_answer=official,
                    tool_calls=tool_calls,
                )
            if subject == "chemistry":
                ok, calls, detail = chem_verify_numeric(message, official)
            else:
                ok, calls, detail = verify_numeric_submission(message, official)
            tool_calls.extend(calls)
            if ok:
                checks_passed.append("numeric_match")
                return VerificationReport(
                    status=VerificationStatus.VERIFIED,
                    confidence=0.95,
                    summary=f"Correct — {detail}",
                    official_answer=official,
                    submitted_answer=message[:120],
                    tool_calls=tool_calls,
                    checks_passed=checks_passed,
                )
            if calls and not calls[-1].success:
                checks_failed.append("numeric_match")
                return VerificationReport(
                    status=VerificationStatus.INCORRECT,
                    confidence=0.9,
                    summary=detail,
                    official_answer=official,
                    submitted_answer=message[:120],
                    tool_calls=tool_calls,
                    checks_failed=checks_failed,
                )
            return VerificationReport(
                status=VerificationStatus.PENDING,
                confidence=0.4,
                summary="Could not verify numeric answer — please state your value clearly.",
                official_answer=official,
                tool_calls=tool_calls,
            )

        if official and official.upper() in "ABCD":
            submitted = extract_submitted_option(message)
            if not submitted:
                lower = message.lower()
                if official.upper() in message.upper() and any(
                    w in lower for w in ("answer is", "i think", "got", "choose")
                ):
                    submitted = official.upper()
                else:
                    return VerificationReport(
                        status=VerificationStatus.PENDING,
                        confidence=0.3,
                        summary="Please specify which option (A, B, C, or D) you chose.",
                        official_answer=official,
                        tool_calls=tool_calls,
                    )

            if subject == "physics":
                ok, call = physics_match_option(submitted, official)
            else:
                ok, call = match_mcq_option(submitted, official)
            tool_calls.append(call)

            if ok:
                checks_passed.append("mcq_match")
                return VerificationReport(
                    status=VerificationStatus.VERIFIED,
                    confidence=0.98,
                    summary=f"Correct — the answer is option {official.upper()}.",
                    official_answer=official.upper(),
                    submitted_answer=submitted,
                    tool_calls=tool_calls,
                    checks_passed=checks_passed,
                )

            checks_failed.append("mcq_match")
            return VerificationReport(
                status=VerificationStatus.INCORRECT,
                confidence=0.95,
                summary=f"Not quite — option {submitted} is incorrect.",
                official_answer=official.upper(),
                submitted_answer=submitted,
                tool_calls=tool_calls,
                checks_failed=checks_failed,
            )

        return VerificationReport(
            status=VerificationStatus.UNVERIFIED,
            confidence=0.2,
            summary="No verified answer key available for this question.",
            official_answer=official,
            tool_calls=tool_calls,
        )
    except Exception as exc:
        tool_calls.append(
            ToolCallRecord(
                tool="answer_checker.verify",
                input_summary=message[:60],
                output_summary="exception",
                success=False,
                error=str(exc),
            )
        )
        return VerificationReport(
            status=VerificationStatus.TOOL_FAILURE,
            confidence=0.0,
            summary="Verification tool error — session continues safely.",
            tool_calls=tool_calls,
            checks_failed=["tool_exception"],
            metadata={"error": str(exc)},
        )
