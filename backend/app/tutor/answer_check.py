"""Backward-compatible answer check — delegates to verification service."""

from __future__ import annotations

from typing import Any, Optional

from app.tutor.schemas import NextAction, VerificationStatus
from app.verification.answer_checker import extract_submitted_option, get_official_answer
from app.verification.service import VerificationService

_service = VerificationService()


def get_correct_answer(question: dict[str, Any]) -> Optional[str]:
    ans = get_official_answer(question)
    return ans.upper() if ans and ans.upper() in "ABCD" else ans


def check_answer(
    message: str, question: Optional[dict[str, Any]]
) -> tuple[VerificationStatus, NextAction, str]:
    report = _service.verify_attempt(message, question)
    status = VerificationStatus(report.status.value)
    if status == VerificationStatus.VERIFIED:
        return status, NextAction.CONTINUE, report.summary
    if status == VerificationStatus.INCORRECT:
        return status, NextAction.TRY_AGAIN, report.summary
    if status == VerificationStatus.PENDING:
        return status, NextAction.TRY_AGAIN, report.summary
    if status == VerificationStatus.TOOL_FAILURE:
        return VerificationStatus.UNVERIFIED, NextAction.CONTINUE, report.summary
    return status, NextAction.CONTINUE, report.summary


from app.verification.text_utils import response_reveals_answer
