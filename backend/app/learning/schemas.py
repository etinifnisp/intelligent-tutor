"""Learning state schemas."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class BKTParams(BaseModel):
    p_known: float = 0.2
    p_learn: float = 0.15
    p_guess: float = 0.2
    p_slip: float = 0.1


class ConceptBKTState(BaseModel):
    concept_id: str
    p_known: float = 0.2
    attempt_count: int = 0
    correct_count: int = 0
    correct_without_hints: int = 0
    correct_after_delay: int = 0
    last_practised_at: Optional[str] = None
    next_review_at: Optional[str] = None
    evidence_sufficient: bool = False


class AttemptEvidence(BaseModel):
    user_id: str
    question_id: str
    concept_ids: list[str] = Field(default_factory=list)
    is_correct: bool
    hints_used: int = 0
    max_hint_level: int = 0
    response_time_ms: Optional[int] = None
    confidence_before: Optional[float] = None
    solution_revealed: bool = False
    subject: str = ""
    chapter: str = ""
    difficulty: str = "Medium"


class MasteryUpdateResult(BaseModel):
    concept_id: str
    p_known_before: float
    p_known_after: float
    delta: float
    mastered: bool
    evidence_weight: float
    reason: str


class RevisionItem(BaseModel):
    concept_id: str
    subject: str = ""
    p_known: float
    next_review_at: str
    reason: str


class QuestionRecommendation(BaseModel):
    question_id: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    subject: str = ""
    chapter: str = ""
    difficulty: str = ""


class LearnerSummary(BaseModel):
    user_id: str
    mastered_concepts: list[str] = Field(default_factory=list)
    weak_concepts: list[str] = Field(default_factory=list)
    misconceptions: dict[str, str] = Field(default_factory=dict)
    revision_due: list[RevisionItem] = Field(default_factory=list)
    total_attempts: int = 0
    narrative: str = ""
