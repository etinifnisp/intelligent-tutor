"""Bayesian Knowledge Tracing — local 4-parameter model."""

from __future__ import annotations

from app.learning.schemas import BKTParams, ConceptBKTState, MasteryUpdateResult


class BKTEngine:
    """Classic BKT update with evidence weighting for hints and solution reveal."""

    def __init__(self, params: BKTParams | None = None) -> None:
        self.params = params or BKTParams()

    def evidence_weight(
        self,
        *,
        hints_used: int,
        max_hint_level: int,
        solution_revealed: bool,
    ) -> float:
        if solution_revealed:
            return 0.1
        weight = 1.0
        weight -= min(hints_used, 5) * 0.12
        if max_hint_level >= 3:
            weight -= 0.2
        return max(0.05, min(1.0, weight))

    def update(
        self,
        state: ConceptBKTState,
        *,
        is_correct: bool,
        evidence_weight: float = 1.0,
        practised_at: str,
        after_delay: bool = False,
    ) -> MasteryUpdateResult:
        p = self.params
        prior = state.p_known

        if is_correct:
            num = prior * (1 - p.p_slip)
            den = num + (1 - prior) * p.p_guess
            posterior = num / den if den else prior
        else:
            num = prior * p.p_slip
            den = num + (1 - prior) * (1 - p.p_guess)
            posterior = num / den if den else prior

        learned = posterior + (1 - posterior) * p.p_learn
        delta = (learned - prior) * evidence_weight
        new_p = max(0.0, min(1.0, prior + delta))

        state.p_known = round(new_p, 4)
        state.attempt_count += 1
        state.last_practised_at = practised_at
        if is_correct:
            state.correct_count += 1
            if evidence_weight >= 0.7:
                state.correct_without_hints += 1
            if after_delay:
                state.correct_after_delay += 1

        state.evidence_sufficient = self.is_mastered(state)

        return MasteryUpdateResult(
            concept_id=state.concept_id,
            p_known_before=round(prior, 4),
            p_known_after=state.p_known,
            delta=round(delta, 4),
            mastered=state.evidence_sufficient,
            evidence_weight=round(evidence_weight, 3),
            reason=self._reason(is_correct, evidence_weight),
        )

    def is_mastered(self, state: ConceptBKTState) -> bool:
        return (
            state.p_known >= 0.85
            and state.correct_count >= 3
            and state.correct_without_hints >= 1
        )

    def _reason(self, is_correct: bool, weight: float) -> str:
        if not is_correct:
            return "incorrect_attempt"
        if weight < 0.3:
            return "correct_with_heavy_hints"
        if weight < 0.7:
            return "correct_with_some_hints"
        return "correct_independent"
