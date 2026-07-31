"""Pedagogy policy — hint ladder and answer-reveal constraints."""

from __future__ import annotations

from app.tutor.schemas import IntentClassification, PedagogyDirective, PedagogyMode, TutorIntent

_HINT_CONSTRAINTS = {
    1: (
        "HINT LEVEL 1 — Recall only. Ask the student to recall the relevant principle or law. "
        "Do NOT name the formula, setup, or final answer."
    ),
    2: (
        "HINT LEVEL 2 — Identify the formula or next reasoning step. "
        "Do NOT complete the calculation or reveal the final answer."
    ),
    3: (
        "HINT LEVEL 3 — Show the problem setup and variable substitution. "
        "Do NOT give the final numerical answer or option letter."
    ),
}


class PedagogyPolicy:
    """Select tutoring mode and hint-level constraints."""

    def get_hint_level(self, learner_memory: dict, question_id: str | None, message: str) -> int:
        levels = learner_memory.setdefault("hint_levels", {})
        key = question_id or "_general"
        current = int(levels.get(key, 1))
        lower = message.lower().strip()
        if any(w in lower for w in ("another hint", "more hint", "next hint", "still stuck")):
            current = min(3, current + 1)
        elif lower in {"a", "option a"} or "step by step" in lower:
            current = max(current, 1)
        levels[key] = current
        return current

    def select(
        self,
        classification: IntentClassification,
        *,
        hint_level: int = 1,
        student_requested_solution: bool = False,
    ) -> PedagogyDirective:
        mode = classification.pedagogy_mode

        if classification.intent == TutorIntent.FULL_SOLUTION or student_requested_solution:
            return PedagogyDirective(
                mode=PedagogyMode.SOLVE,
                hint_level=4,
                reveal_answer=True,
                system_constraints=(
                    "Provide a complete, step-by-step verified solution. "
                    "State the final answer clearly at the end."
                ),
            )

        if mode == PedagogyMode.HINT:
            level = min(3, max(1, hint_level))
            return PedagogyDirective(
                mode=PedagogyMode.HINT,
                hint_level=level,
                reveal_answer=False,
                system_constraints=_HINT_CONSTRAINTS[level],
            )

        if mode == PedagogyMode.CHECK:
            return PedagogyDirective(
                mode=PedagogyMode.CHECK,
                hint_level=0,
                reveal_answer=False,
                system_constraints=(
                    "Evaluate the student's submitted answer or reasoning. "
                    "Confirm correctness or explain the mistake without giving away the full solution "
                    "unless they explicitly asked for it."
                ),
            )

        if mode == PedagogyMode.PRACTICE:
            return PedagogyDirective(
                mode=PedagogyMode.PRACTICE,
                hint_level=0,
                reveal_answer=False,
                system_constraints=(
                    "Provide graded practice questions (Easy, Medium, Hard) on the active concept. "
                    "Do not reveal answers immediately — ask the student to attempt first."
                ),
            )

        if mode == PedagogyMode.REVISE:
            return PedagogyDirective(
                mode=PedagogyMode.REVISE,
                hint_level=0,
                reveal_answer=False,
                system_constraints="Create a focused revision plan using weak concepts from the learner profile.",
            )

        return PedagogyDirective(
            mode=PedagogyMode.LEARN,
            hint_level=0,
            reveal_answer=False,
            system_constraints="Explain clearly and concisely. Use examples when helpful.",
        )

    def strip_answer_from_context(self, question: dict | None, reveal: bool) -> dict | None:
        """Remove answer key from question context when hints should not reveal it."""
        if not question or reveal:
            return question
        safe = dict(question)
        safe.pop("correct_answer", None)
        safe.pop("official_solution", None)
        if "answer" in safe:
            safe.pop("answer")
        return safe
