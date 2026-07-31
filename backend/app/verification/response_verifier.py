"""Second-pass response verification — rule-based, no code execution."""

from __future__ import annotations

import re
from typing import Optional

from app.verification.text_utils import response_reveals_answer
from app.verification.schemas import VerificationReport, VerificationStatus

_CORRECT_CLAIM_RE = re.compile(
    r"\b(correct|that'?s right|well done|perfect|exactly right)\b", re.I
)
_INCORRECT_CLAIM_RE = re.compile(
    r"\b(incorrect|not quite|wrong|that'?s not right|mistake)\b", re.I
)
_ANSWER_CLAIM_RE = re.compile(
    r"(?:the\s+)?(?:correct\s+)?answer\s+is\s+(?:option\s+)?([a-d]|\d+(?:\.\d+)?)",
    re.I,
)


def verify_model_response(
    response_text: str,
    attempt_report: Optional[VerificationReport],
    *,
    pedagogy_mode: str,
    hint_level: int,
    official_answer: Optional[str],
    reveal_answer: bool,
) -> VerificationReport:
    """Check model output against deterministic attempt verification."""
    tool_calls = []
    checks_passed: list[str] = []
    checks_failed: list[str] = []
    lower = response_text.lower()

    if pedagogy_mode == "HINT" and not reveal_answer:
        if response_reveals_answer(response_text, official_answer):
            checks_failed.append("hint_leak")
            return VerificationReport(
                status=VerificationStatus.UNVERIFIED,
                confidence=0.3,
                summary="Model response reveals answer during hint mode.",
                tool_calls=tool_calls,
                checks_failed=checks_failed,
            )
        checks_passed.append("hint_safe")

    if not attempt_report or attempt_report.status in {
        VerificationStatus.UNVERIFIED,
        VerificationStatus.PENDING,
        VerificationStatus.TOOL_FAILURE,
    }:
        m = _ANSWER_CLAIM_RE.search(response_text)
        if m and official_answer:
            claimed = m.group(1).upper()
            if claimed != str(official_answer).upper():
                checks_failed.append("unsourced_answer_claim")
                return VerificationReport(
                    status=VerificationStatus.UNVERIFIED,
                    confidence=0.4,
                    summary="Model stated an answer that could not be verified.",
                    tool_calls=tool_calls,
                    checks_failed=checks_failed,
                )
        return VerificationReport(
            status=VerificationStatus.PARTIALLY_VERIFIED if checks_passed else VerificationStatus.UNVERIFIED,
            confidence=0.5,
            summary="Response not fully verifiable.",
            tool_calls=tool_calls,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )

    attempt_status = attempt_report.status

    if attempt_status == VerificationStatus.VERIFIED:
        if _INCORRECT_CLAIM_RE.search(response_text):
            checks_failed.append("contradicts_verified_correct")
            return VerificationReport(
                status=VerificationStatus.CONFLICTING_SOURCE,
                confidence=0.1,
                summary="Model contradicts verified correct answer.",
                tool_calls=tool_calls,
                checks_failed=checks_failed,
            )
        if _CORRECT_CLAIM_RE.search(response_text) or "correct" in lower:
            checks_passed.append("aligns_with_verified")
            return VerificationReport(
                status=VerificationStatus.VERIFIED,
                confidence=0.92,
                summary="Response aligns with verified correct answer.",
                tool_calls=tool_calls,
                checks_passed=checks_passed,
            )
        return VerificationReport(
            status=VerificationStatus.PARTIALLY_VERIFIED,
            confidence=0.75,
            summary="Attempt verified; response neutral.",
            tool_calls=tool_calls,
            checks_passed=checks_passed,
        )

    if attempt_status == VerificationStatus.INCORRECT:
        if _CORRECT_CLAIM_RE.search(response_text) and "not" not in lower[: lower.find("correct") + 1]:
            checks_failed.append("false_positive")
            return VerificationReport(
                status=VerificationStatus.CONFLICTING_SOURCE,
                confidence=0.1,
                summary="Model incorrectly affirmed a wrong answer.",
                tool_calls=tool_calls,
                checks_failed=checks_failed,
            )
        checks_passed.append("aligns_with_incorrect")
        return VerificationReport(
            status=VerificationStatus.VERIFIED,
            confidence=0.88,
            summary="Response correctly identifies incorrect attempt.",
            tool_calls=tool_calls,
            checks_passed=checks_passed,
        )

    return VerificationReport(
        status=VerificationStatus.UNVERIFIED,
        confidence=0.4,
        summary="Could not verify response against attempt.",
        tool_calls=tool_calls,
    )
