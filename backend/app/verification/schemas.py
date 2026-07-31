"""Verification schemas and tool-call records."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    INCORRECT = "INCORRECT"
    CONFLICTING_SOURCE = "CONFLICTING_SOURCE"
    TOOL_FAILURE = "TOOL_FAILURE"


class ToolCallRecord(BaseModel):
    tool: str
    input_summary: str
    output_summary: str
    success: bool = True
    error: Optional[str] = None


class VerificationReport(BaseModel):
    status: VerificationStatus
    confidence: float = 0.0
    summary: str = ""
    official_answer: Optional[str] = None
    submitted_answer: Optional[str] = None
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    checks_passed: list[str] = Field(default_factory=list)
    checks_failed: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
