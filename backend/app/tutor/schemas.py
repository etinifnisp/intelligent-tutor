"""Structured tutor request/response schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TutorIntent(str, Enum):
    GREETING = "GREETING"
    CONCEPT_EXPLANATION = "CONCEPT_EXPLANATION"
    HINT_REQUEST = "HINT_REQUEST"
    ANSWER_CHECK = "ANSWER_CHECK"
    FULL_SOLUTION = "FULL_SOLUTION"
    ERROR_EXPLANATION = "ERROR_EXPLANATION"
    DIAGNOSTIC_QUESTION = "DIAGNOSTIC_QUESTION"
    PRACTICE_REQUEST = "PRACTICE_REQUEST"
    QUESTION_SEARCH = "QUESTION_SEARCH"
    REVISION_PLAN = "REVISION_PLAN"
    PROGRESS_QUERY = "PROGRESS_QUERY"
    OFF_TOPIC = "OFF_TOPIC"


class PedagogyMode(str, Enum):
    LEARN = "LEARN"
    HINT = "HINT"
    SOLVE = "SOLVE"
    CHECK = "CHECK"
    PRACTICE = "PRACTICE"
    REVISE = "REVISE"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    INCORRECT = "INCORRECT"
    CONFLICTING_SOURCE = "CONFLICTING_SOURCE"
    TOOL_FAILURE = "TOOL_FAILURE"


class NextAction(str, Enum):
    TRY_AGAIN = "TRY_AGAIN"
    ASK_HINT = "ASK_HINT"
    SHOW_SOLUTION = "SHOW_SOLUTION"
    PRACTICE_MORE = "PRACTICE_MORE"
    CONTINUE = "CONTINUE"


class IntentClassification(BaseModel):
    intent: TutorIntent
    confidence: float = 0.85
    requires_retrieval: bool = False
    requires_verification: bool = False
    pedagogy_mode: PedagogyMode = PedagogyMode.LEARN
    lane: str = "DIRECT"  # legacy: PIPELINE | DIRECT


class PedagogyDirective(BaseModel):
    mode: PedagogyMode
    hint_level: int = 1
    max_hint_level: int = 3
    reveal_answer: bool = False
    system_constraints: str = ""


class TutorResponse(BaseModel):
    message: str
    intent: TutorIntent
    verification_status: VerificationStatus
    hint_level: int = 0
    concepts: list[str] = Field(default_factory=list)
    next_action: NextAction = NextAction.CONTINUE
    mastery_update_allowed: bool = False
    source_question_id: Optional[str] = None
    pedagogy_mode: PedagogyMode = PedagogyMode.LEARN
    prompt_version: str = "v1.0.0"
    model_name: str = ""
    answer_confidence: float = 0.0
    verification_report: dict[str, Any] = Field(default_factory=dict)


class TutorContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: str
    student_message: str
    question_id: Optional[str] = None
    chapter_context: Optional[str] = None
    chat_history: list[dict[str, Any]] = Field(default_factory=list)
    conversation_id: Optional[str] = None

    # Resolved at runtime
    target_question: Optional[dict[str, Any]] = None
    active_chapter: str = "General"
    active_subject: str = ""
    active_concept_node: Optional[str] = None
    learner_memory: dict[str, Any] = Field(default_factory=dict)
    graph_ctx: dict[str, Any] = Field(default_factory=dict)
    related_questions: dict[str, Any] = Field(default_factory=dict)
