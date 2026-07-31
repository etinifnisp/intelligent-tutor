"""Misconception classification from attempt evidence."""

from __future__ import annotations

from app.learning.schemas import AttemptEvidence

CATEGORIES = {
    "conceptual_gap": "Fundamental concept misunderstanding",
    "formula_error": "Wrong formula or relationship applied",
    "calculation_error": "Arithmetic or algebraic slip",
    "unit_error": "Unit or dimensional mistake",
    "careless_mistake": "Fast incorrect response with high confidence",
    "hint_dependency": "Repeated incorrect attempts after hints",
}


class MisconceptionClassifier:
    def classify(self, evidence: AttemptEvidence) -> str | None:
        if evidence.is_correct:
            return None

        if evidence.confidence_before and evidence.confidence_before >= 0.8:
            if evidence.response_time_ms and evidence.response_time_ms < 8000:
                return "careless_mistake"

        if evidence.hints_used >= 2 or evidence.max_hint_level >= 2:
            return "hint_dependency"

        subject = evidence.subject.lower()
        if subject == "physics":
            return "formula_error"
        if subject == "chemistry":
            return "conceptual_gap"
        if subject == "mathematics":
            return "calculation_error"
        return "conceptual_gap"

    def description(self, category: str) -> str:
        return CATEGORIES.get(category, "Unknown misconception pattern")
