"""Phase 5 orchestrator tests — mock model, no external APIs."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.tutor.answer_check import check_answer, response_reveals_answer
from app.tutor.model_gateway import MockModelGateway
from app.tutor.orchestrator import TutorOrchestrator
from app.tutor.pedagogy import PedagogyPolicy
from app.tutor.router import IntentRouter
from app.tutor.schemas import TutorContext, TutorIntent, VerificationStatus
from app.verification.service import VerificationService


@pytest.fixture
def sample_question():
    return {
        "question_id": "jee_main_2024_test_q1",
        "id": "jee_main_2024_test_q1",
        "subject": "Physics",
        "chapter": "Mechanics",
        "raw_text": "A block slides down a frictionless incline.",
        "correct_answer": "B",
    }


def test_intent_router_answer_check():
    router = IntentRouter()
    result = router.classify("Is option B correct?", has_question=True)
    assert result.intent == TutorIntent.ANSWER_CHECK
    assert result.requires_verification is True


def test_intent_router_hint():
    router = IntentRouter()
    result = router.classify("Can I get a hint?", has_question=True)
    assert result.intent == TutorIntent.HINT_REQUEST
    assert result.pedagogy_mode.value == "HINT"


def test_pedagogy_hint_does_not_reveal_answer():
    policy = PedagogyPolicy()
    safe = policy.strip_answer_from_context({"correct_answer": "B", "stem_text": "Q"}, reveal=False)
    assert "correct_answer" not in safe


def test_answer_check_resolves_correct_option(sample_question):
    status, action, summary = check_answer("I think option B is correct", sample_question)
    assert status == VerificationStatus.VERIFIED
    assert "Correct" in summary
    assert action.value == "CONTINUE"


def test_answer_check_detects_wrong_option(sample_question):
    status, _, _ = check_answer("Is option A correct?", sample_question)
    assert status == VerificationStatus.INCORRECT


def test_response_reveals_answer_detection():
    assert response_reveals_answer("The correct answer is option B.", "B") is True
    assert response_reveals_answer("Recall Newton's second law.", "B") is False


@pytest.mark.asyncio
async def test_orchestrator_emits_intent_and_verification(sample_question):
    mock = MockModelGateway("Recall the relevant physics principle first.")
    orchestrator = TutorOrchestrator(model_gateway=mock)

    graph = MagicMock()
    graph.get_graph_rag_context.return_value = {
        "active_concept": "Mechanics",
        "current_mastery": 0.4,
        "prereq_chain": [],
        "unmastered_prereqs": [],
        "hint_scaffolds": [],
        "graph_hint": "Start with forces.",
        "misconceptions": None,
    }
    graph.get_questions_by_concept.return_value = {}
    graph.get_learner_memory.return_value = {"mastery": {}, "misconceptions": {}, "session_history": []}
    graph.write_learner_memory = MagicMock()
    graph.update_concept_mastery_on_graph = MagicMock()

    retrieval = MagicMock()
    retrieval.ready = True
    retrieval.search.return_value = []
    retrieval.format_evidence_block.return_value = "No retrieved evidence."
    retrieval.concept_note.return_value = None

    verification = VerificationService()

    app_state = SimpleNamespace(graph=graph, retrieval=retrieval, verification=verification)

    ctx = TutorContext(
        user_id="user-1",
        student_message="Is option B correct?",
        question_id=sample_question["question_id"],
        target_question=sample_question,
        active_chapter="Mechanics",
        active_subject="Physics",
        active_concept_node="Mechanics",
        learner_memory={"mastery": {}, "misconceptions": {}, "session_history": [], "hint_levels": {}},
    )

    events = []
    async for event in orchestrator.handle_message(ctx, app_state):
        events.append(event)

    meta = next(e for e in events if e["type"] == "tutor_meta")["data"]
    assert meta["intent"] == TutorIntent.ANSWER_CHECK.value
    assert meta["verification_status"] in {
        VerificationStatus.VERIFIED.value,
        VerificationStatus.UNVERIFIED.value,
        VerificationStatus.PENDING.value,
        VerificationStatus.PARTIALLY_VERIFIED.value,
    }
    assert meta["verification_status"] == VerificationStatus.VERIFIED.value
    assert "Recall" in meta["message"]


@pytest.mark.asyncio
async def test_hint_mode_with_mock_model(sample_question):
    revealing_mock = MockModelGateway("The answer is option B.")
    orchestrator = TutorOrchestrator(model_gateway=revealing_mock)

    graph = MagicMock()
    graph.get_graph_rag_context.return_value = {
        "active_concept": "Mechanics",
        "current_mastery": 0.2,
        "prereq_chain": [],
        "unmastered_prereqs": [],
        "hint_scaffolds": [],
        "graph_hint": "",
        "misconceptions": None,
    }
    graph.get_questions_by_concept.return_value = {}
    graph.write_learner_memory = MagicMock()
    graph.update_concept_mastery_on_graph = MagicMock()

    retrieval = MagicMock()
    retrieval.ready = False

    verification = VerificationService()

    app_state = SimpleNamespace(graph=graph, retrieval=retrieval, verification=verification)

    ctx = TutorContext(
        user_id="user-2",
        student_message="I need a hint",
        question_id=sample_question["question_id"],
        target_question=sample_question,
        active_chapter="Mechanics",
        active_subject="Physics",
        active_concept_node="Mechanics",
        learner_memory={"mastery": {}, "misconceptions": {}, "session_history": [], "hint_levels": {}},
    )

    events = []
    async for event in orchestrator.handle_message(ctx, app_state):
        events.append(event)

    meta = next(e for e in events if e["type"] == "tutor_meta")["data"]
    assert meta["intent"] == TutorIntent.HINT_REQUEST.value
    assert meta["hint_level"] >= 1
    assert "Hint sanitized" in meta["message"] or meta["verification_status"] != VerificationStatus.VERIFIED.value


def test_mock_model_gateway_streams():
    async def _run():
        gw = MockModelGateway("hello world")
        chunks = []
        async for part in gw.generate_stream("sys", [{"role": "user", "content": "hi"}]):
            chunks.append(part)
        return "".join(chunks)

    text = asyncio.run(_run())
    assert "hello world" in text
