"""Adaptive next-question selection with explainable scoring."""

from __future__ import annotations

from typing import Any, Callable

from app.learning.schemas import ConceptBKTState, QuestionRecommendation


class AdaptiveQuestionSelector:
    def score_question(
        self,
        question: dict[str, Any],
        concept_states: dict[str, ConceptBKTState],
        concept_ids: list[str],
        *,
        revision_targets: set[str] | None = None,
    ) -> QuestionRecommendation:
        revision_targets = revision_targets or set()
        qid = (
            question.get("question_id")
            or question.get("id")
            or (f"q_{question['question_number']}" if question.get("question_number") is not None else "")
        )
        chapter = question.get("chapter", "")
        subject = question.get("subject", "")
        difficulty = question.get("difficulty") or question.get("question_type") or "Medium"

        reasons: list[str] = []
        score = 0.0

        p_values = [concept_states[c].p_known for c in concept_ids if c in concept_states]
        avg_p = sum(p_values) / len(p_values) if p_values else 0.3

        if any(c in revision_targets for c in concept_ids):
            score += 0.4
            reasons.append("targets_due_revision_concept")

        if 0.35 <= avg_p <= 0.75:
            score += 0.35
            reasons.append("zone_of_proximal_development")
        elif avg_p < 0.35:
            score += 0.2
            reasons.append("foundational_practice_for_weak_concept")
        else:
            score += 0.1
            reasons.append("maintenance_practice")

        diff = str(difficulty).lower()
        if "easy" in diff:
            score += 0.15 if avg_p < 0.5 else 0.05
            reasons.append("difficulty_easy")
        elif "hard" in diff:
            score += 0.15 if avg_p >= 0.6 else 0.05
            reasons.append("difficulty_hard")
        else:
            score += 0.1
            reasons.append("difficulty_medium")

        if question.get("review_status") == "REVIEWED":
            score += 0.1
            reasons.append("reviewed_corpus_source")

        return QuestionRecommendation(
            question_id=qid,
            score=round(score, 4),
            reasons=reasons,
            subject=subject,
            chapter=chapter,
            difficulty=str(difficulty),
        )

    def select_next(
        self,
        questions: list[dict[str, Any]],
        concept_states: dict[str, ConceptBKTState],
        concept_resolver: Callable[[dict[str, Any]], list[str]],
        *,
        revision_targets: set[str] | None = None,
        subject: str = "",
        limit: int = 5,
    ) -> list[QuestionRecommendation]:
        scored: list[QuestionRecommendation] = []
        for q in questions:
            if subject and q.get("subject") != subject:
                continue
            concepts = concept_resolver(q)
            if not concepts:
                continue
            rec = self.score_question(q, concept_states, concepts, revision_targets=revision_targets)
            if rec.question_id:
                scored.append(rec)
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]
