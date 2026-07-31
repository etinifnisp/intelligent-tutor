"""Verification service — orchestrates deterministic checks with tool logging."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.verification.answer_checker import get_official_answer, verify_student_answer
from app.verification.response_verifier import verify_model_response
from app.verification.schemas import VerificationReport, VerificationStatus

logger = logging.getLogger("tutor.verification")


class VerificationService:
    def verify_attempt(self, message: str, question: Optional[dict[str, Any]]) -> VerificationReport:
        report = verify_student_answer(message, question)
        for call in report.tool_calls:
            level = logging.DEBUG if call.success else logging.WARNING
            logger.log(
                level,
                "tool_call %s success=%s in=%s out=%s err=%s",
                call.tool,
                call.success,
                call.input_summary,
                call.output_summary,
                call.error,
            )
        return report

    def verify_response(
        self,
        response_text: str,
        attempt_report: Optional[VerificationReport],
        *,
        pedagogy_mode: str,
        hint_level: int,
        question: Optional[dict[str, Any]],
        reveal_answer: bool,
    ) -> VerificationReport:
        official = get_official_answer(question) if question else None
        report = verify_model_response(
            response_text,
            attempt_report,
            pedagogy_mode=pedagogy_mode,
            hint_level=hint_level,
            official_answer=official,
            reveal_answer=reveal_answer,
        )
        for call in report.tool_calls:
            logger.debug("response_verify tool=%s success=%s", call.tool, call.success)
        return report

    def merge_status(
        self,
        attempt: VerificationReport,
        response: VerificationReport,
    ) -> tuple[VerificationStatus, float]:
        """Final status prioritizes conflicts and tool failures."""
        if response.status == VerificationStatus.CONFLICTING_SOURCE:
            return VerificationStatus.UNVERIFIED, min(attempt.confidence, response.confidence)
        if attempt.status == VerificationStatus.TOOL_FAILURE:
            return VerificationStatus.TOOL_FAILURE, 0.0
        if attempt.status == VerificationStatus.VERIFIED:
            if response.status == VerificationStatus.UNVERIFIED:
                return VerificationStatus.UNVERIFIED, min(attempt.confidence, response.confidence)
            return VerificationStatus.VERIFIED, max(attempt.confidence, response.confidence)
        if attempt.status == VerificationStatus.INCORRECT:
            if response.status == VerificationStatus.CONFLICTING_SOURCE:
                return VerificationStatus.UNVERIFIED, 0.2
            return VerificationStatus.INCORRECT, attempt.confidence
        if response.status in {VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED}:
            return response.status, max(attempt.confidence, response.confidence)
        return attempt.status, attempt.confidence
