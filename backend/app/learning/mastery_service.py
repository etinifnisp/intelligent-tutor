"""Mastery service — evidence-based BKT updates and learner summaries."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.learning.bkt import BKTEngine
from app.learning.misconception import MisconceptionClassifier
from app.learning.question_selector import AdaptiveQuestionSelector
from app.learning.revision_scheduler import RevisionScheduler
from app.learning.schemas import (
    AttemptEvidence,
    ConceptBKTState,
    LearnerSummary,
    MasteryUpdateResult,
    QuestionRecommendation,
    RevisionItem,
)
from app.services.learner_store import LearnerStore

logger = logging.getLogger("tutor.learning")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MasteryService:
    def __init__(self, learner_store: LearnerStore | None = None) -> None:
        self.store = learner_store or LearnerStore()
        self.bkt = BKTEngine()
        self.misconceptions = MisconceptionClassifier()
        self.revision = RevisionScheduler()
        self.selector = AdaptiveQuestionSelector()

    def _ensure_learning_state(self, memory: dict[str, Any]) -> dict[str, Any]:
        memory.setdefault("bkt_states", {})
        memory.setdefault("revision_queue", [])
        memory.setdefault("concept_subjects", {})
        memory.setdefault("mastery", {})
        memory.setdefault("misconceptions", {})
        memory.setdefault("session_history", [])
        return memory

    def _get_bkt_state(self, memory: dict, concept_id: str) -> ConceptBKTState:
        raw = memory["bkt_states"].get(concept_id)
        if raw:
            return ConceptBKTState(**raw)
        return ConceptBKTState(concept_id=concept_id)

    def _save_bkt_state(self, memory: dict, state: ConceptBKTState) -> None:
        memory["bkt_states"][state.concept_id] = state.model_dump()
        memory["mastery"][state.concept_id] = round(state.p_known, 2)

    def resolve_concepts(
        self,
        graph: Any,
        question_id: Optional[str],
        chapter: str,
        subject: str,
    ) -> list[str]:
        concepts: list[str] = []
        if question_id and hasattr(graph, "G") and question_id in graph.G:
            for _, tgt, d in graph.G.out_edges(question_id, data=True):
                if d.get("type") == "tests_concept":
                    concepts.append(tgt)
        if not concepts and chapter and chapter != "General":
            node = graph._find_chapter_node(chapter, subject) if hasattr(graph, "_find_chapter_node") else chapter
            concepts.append(node or chapter)
        return concepts

    def record_attempt(
        self,
        evidence: AttemptEvidence,
        graph: Any,
    ) -> list[MasteryUpdateResult]:
        """Update mastery only from verified attempt evidence."""
        if evidence.is_correct is None:
            return []

        memory = self._ensure_learning_state(self.store.get_memory(evidence.user_id))
        concept_ids = evidence.concept_ids or self.resolve_concepts(
            graph, evidence.question_id, evidence.chapter, evidence.subject
        )
        if not concept_ids:
            return []

        weight = self.bkt.evidence_weight(
            hints_used=evidence.hints_used,
            max_hint_level=evidence.max_hint_level,
            solution_revealed=evidence.solution_revealed,
        )
        after_delay = False
        now = _utc_now()
        results: list[MasteryUpdateResult] = []

        for concept_id in concept_ids:
            state = self._get_bkt_state(memory, concept_id)
            if state.last_practised_at:
                try:
                    last = datetime.fromisoformat(state.last_practised_at)
                    after_delay = (datetime.now(timezone.utc) - last).total_seconds() > 86400
                except ValueError:
                    after_delay = False

            result = self.bkt.update(
                state,
                is_correct=evidence.is_correct,
                evidence_weight=weight,
                practised_at=now,
                after_delay=after_delay,
            )
            self._save_bkt_state(memory, state)
            memory["concept_subjects"][concept_id] = evidence.subject

            rev = self.revision.schedule(
                concept_id, state, subject=evidence.subject, is_correct=evidence.is_correct
            )
            if rev:
                memory["revision_queue"] = [
                    r for r in memory.get("revision_queue", []) if r.get("concept_id") != concept_id
                ]
                memory["revision_queue"].append(rev.model_dump())

            if not evidence.is_correct:
                cat = self.misconceptions.classify(evidence)
                if cat:
                    memory["misconceptions"][concept_id] = self.misconceptions.description(cat)

            results.append(result)
            logger.info(
                "BKT update user=%s concept=%s %.3f→%.3f weight=%.2f",
                evidence.user_id,
                concept_id,
                result.p_known_before,
                result.p_known_after,
                weight,
            )

        self.store.save_memory(evidence.user_id, memory)
        if hasattr(graph, "write_learner_memory"):
            graph.write_learner_memory(evidence.user_id, memory)
        for r in results:
            if hasattr(graph, "update_concept_mastery_on_graph"):
                graph.update_concept_mastery_on_graph(evidence.user_id, r.concept_id, r.p_known_after)

        return results

    def get_revision_schedule(
        self, user_id: str, *, subject: str = ""
    ) -> list[RevisionItem]:
        memory = self._ensure_learning_state(self.store.get_memory(user_id))
        states = {
            cid: ConceptBKTState(**raw) for cid, raw in memory.get("bkt_states", {}).items()
        }
        return self.revision.due_items(
            states, subject=subject, concept_subjects=memory.get("concept_subjects", {})
        )

    def recommend_questions(
        self,
        user_id: str,
        questions: list[dict[str, Any]],
        graph: Any,
        *,
        subject: str = "",
        limit: int = 5,
    ) -> list[QuestionRecommendation]:
        memory = self._ensure_learning_state(self.store.get_memory(user_id))
        states = {
            cid: ConceptBKTState(**raw) for cid, raw in memory.get("bkt_states", {}).items()
        }
        due = self.get_revision_schedule(user_id, subject=subject)
        targets = {d.concept_id for d in due}

        def resolver(q: dict[str, Any]) -> list[str]:
            qid = q.get("question_id") or q.get("id")
            return self.resolve_concepts(graph, qid, q.get("chapter", ""), q.get("subject", ""))

        return self.selector.select_next(
            questions,
            states,
            resolver,
            revision_targets=targets,
            subject=subject,
            limit=limit,
        )

    def build_summary(self, user_id: str) -> LearnerSummary:
        memory = self._ensure_learning_state(self.store.get_memory(user_id))
        states = {
            cid: ConceptBKTState(**raw) for cid, raw in memory.get("bkt_states", {}).items()
        }
        mastered = [cid for cid, s in states.items() if s.evidence_sufficient]
        weak = [cid for cid, s in states.items() if s.p_known < 0.45]
        due = self.get_revision_schedule(user_id)
        total_attempts = sum(s.attempt_count for s in states.values())

        if weak:
            focus = ", ".join(weak[:3])
            narrative = (
                f"Learner has {total_attempts} concept-level attempts recorded. "
                f"Weak areas needing practice: {focus}. "
                f"{len(due)} concept(s) due for revision."
            )
        elif mastered:
            narrative = (
                f"Learner shows evidence-based mastery in {len(mastered)} concept(s). "
                "Continue spaced revision to retain knowledge."
            )
        else:
            narrative = "Insufficient attempt evidence to assess mastery. Complete practice attempts to build profile."

        return LearnerSummary(
            user_id=user_id,
            mastered_concepts=mastered,
            weak_concepts=weak,
            misconceptions=memory.get("misconceptions", {}),
            revision_due=due,
            total_attempts=total_attempts,
            narrative=narrative,
        )

    def sync_mastery_display(self, memory: dict[str, Any]) -> dict[str, Any]:
        """Keep legacy mastery map in sync with BKT states."""
        memory = self._ensure_learning_state(memory)
        for cid, raw in memory.get("bkt_states", {}).items():
            state = ConceptBKTState(**raw)
            if state.evidence_sufficient:
                memory["mastery"][cid] = round(state.p_known, 2)
            elif state.attempt_count > 0:
                memory["mastery"][cid] = round(state.p_known, 2)
        return memory
