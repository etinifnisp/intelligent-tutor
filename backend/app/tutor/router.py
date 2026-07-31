"""Structured intent classification — rule-based, no model required."""

from __future__ import annotations

import re

from app.tutor.schemas import IntentClassification, PedagogyMode, TutorIntent

_GREETING = re.compile(r"^(hi|hello|hey|thanks|thank you|good morning|good evening)\b", re.I)
_ANSWER_CHECK = re.compile(
    r"\b(is\s+(it|this|my answer)\s+(right|correct)|"
    r"check\s+my\s+answer|"
    r"is\s+option\s+[a-d]\s+(right|correct)|"
    r"did\s+i\s+get\s+it\s+right|"
    r"am\s+i\s+correct)\b",
    re.I,
)
_HINT = re.compile(
    r"\b(hint|clue|stuck|help\s+me\s+solve|step\s+by\s+step|"
    r"please\s+help\s+me\s+solve|guide\s+me|how\s+do\s+i\s+start)\b",
    re.I,
)
_SOLUTION = re.compile(
    r"\b(full\s+solution|show\s+(me\s+)?the\s+answer|solve\s+completely|"
    r"give\s+me\s+the\s+answer|final\s+answer)\b",
    re.I,
)
_CONCEPT = re.compile(
    r"\b(explain|what\s+is|tell\s+me\s+about|define|concept\s+of|"
    r"how\s+does\s+.+\s+work)\b",
    re.I,
)
_PRACTICE = re.compile(r"\b(practice|more\s+questions|give\s+me\s+questions|quiz\s+me)\b", re.I)
_PROGRESS = re.compile(r"\b(my\s+progress|how\s+am\s+i\s+doing|mastery|stats)\b", re.I)
_REVISION = re.compile(r"\b(revise|revision|weak\s+topics|what\s+should\s+i\s+study)\b", re.I)
_ERROR = re.compile(r"\b(why\s+wrong|why\s+is\s+it\s+wrong|my\s+mistake|where\s+did\s+i\s+go\s+wrong)\b", re.I)
_SEARCH = re.compile(r"\b(find\s+questions|search\s+for|questions\s+on|questions\s+about)\b", re.I)
_OPTION_PICK = re.compile(r"^option\s+[a-d]\s*$", re.I)


def _mode_for(intent: TutorIntent) -> PedagogyMode:
    return {
        TutorIntent.HINT_REQUEST: PedagogyMode.HINT,
        TutorIntent.ANSWER_CHECK: PedagogyMode.CHECK,
        TutorIntent.FULL_SOLUTION: PedagogyMode.SOLVE,
        TutorIntent.CONCEPT_EXPLANATION: PedagogyMode.LEARN,
        TutorIntent.PRACTICE_REQUEST: PedagogyMode.PRACTICE,
        TutorIntent.REVISION_PLAN: PedagogyMode.REVISE,
        TutorIntent.ERROR_EXPLANATION: PedagogyMode.HINT,
        TutorIntent.DIAGNOSTIC_QUESTION: PedagogyMode.LEARN,
        TutorIntent.QUESTION_SEARCH: PedagogyMode.PRACTICE,
        TutorIntent.PROGRESS_QUERY: PedagogyMode.LEARN,
        TutorIntent.GREETING: PedagogyMode.LEARN,
        TutorIntent.OFF_TOPIC: PedagogyMode.LEARN,
    }[intent]


def _flags_for(intent: TutorIntent) -> tuple[bool, bool]:
    retrieval = intent in {
        TutorIntent.HINT_REQUEST,
        TutorIntent.ANSWER_CHECK,
        TutorIntent.FULL_SOLUTION,
        TutorIntent.ERROR_EXPLANATION,
        TutorIntent.CONCEPT_EXPLANATION,
        TutorIntent.PRACTICE_REQUEST,
        TutorIntent.QUESTION_SEARCH,
        TutorIntent.DIAGNOSTIC_QUESTION,
    }
    verification = intent in {
        TutorIntent.ANSWER_CHECK,
        TutorIntent.FULL_SOLUTION,
        TutorIntent.ERROR_EXPLANATION,
    }
    return retrieval, verification


class IntentRouter:
    """Classify student messages into structured tutoring intents."""

    def classify(self, message: str, *, has_question: bool = False) -> IntentClassification:
        text = (message or "").strip()
        lower = text.lower()

        if not text:
            intent = TutorIntent.OFF_TOPIC
        elif _GREETING.match(lower):
            intent = TutorIntent.GREETING
        elif _ANSWER_CHECK.search(lower) or _OPTION_PICK.match(lower):
            intent = TutorIntent.ANSWER_CHECK
        elif _SOLUTION.search(lower):
            intent = TutorIntent.FULL_SOLUTION
        elif _HINT.search(lower) or (has_question and lower.startswith("please help me solve")):
            intent = TutorIntent.HINT_REQUEST
        elif _ERROR.search(lower):
            intent = TutorIntent.ERROR_EXPLANATION
        elif _PRACTICE.search(lower) or lower in {"b", "option b"}:
            intent = TutorIntent.PRACTICE_REQUEST
        elif lower in {"a", "option a"} and has_question:
            intent = TutorIntent.HINT_REQUEST
        elif _PROGRESS.search(lower):
            intent = TutorIntent.PROGRESS_QUERY
        elif _REVISION.search(lower):
            intent = TutorIntent.REVISION_PLAN
        elif _SEARCH.search(lower):
            intent = TutorIntent.QUESTION_SEARCH
        elif _CONCEPT.search(lower):
            intent = TutorIntent.CONCEPT_EXPLANATION
        elif has_question and len(text) > 40:
            intent = TutorIntent.HINT_REQUEST
        else:
            intent = TutorIntent.DIAGNOSTIC_QUESTION

        requires_retrieval, requires_verification = _flags_for(intent)
        pedagogy_mode = _mode_for(intent)
        lane = "PIPELINE" if requires_retrieval else "DIRECT"

        return IntentClassification(
            intent=intent,
            confidence=0.9 if intent != TutorIntent.OFF_TOPIC else 0.5,
            requires_retrieval=requires_retrieval,
            requires_verification=requires_verification,
            pedagogy_mode=pedagogy_mode,
            lane=lane,
        )
