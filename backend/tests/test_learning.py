"""Phase 7 learning tests — BKT, revision, evidence-based mastery."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.learning.bkt import BKTEngine
from app.learning.mastery_service import MasteryService
from app.learning.question_selector import AdaptiveQuestionSelector
from app.learning.revision_scheduler import RevisionScheduler
from app.learning.schemas import AttemptEvidence, ConceptBKTState
from app.tutor.orchestrator import TutorOrchestrator
from app.tutor.schemas import TutorContext, TutorIntent, VerificationStatus
from app.tutor.model_gateway import MockModelGateway
from app.verification.service import VerificationService


def test_i_understand_does_not_change_mastery():
    state = ConceptBKTState(concept_id="Mechanics")
    before = state.p_known
    orch = TutorOrchestrator(model_gateway=MockModelGateway("Great!"))
    ctx = TutorContext(
        user_id="u1",
        student_message="I understand now!",
        learner_memory={"mastery": {}, "misconceptions": {}, "session_history": [], "hint_levels": {}},
    )
    delta, event = orch._update_mastery(ctx, MagicMock(), MagicMock())
    assert delta == 0.0
    assert event is None
    assert state.p_known == before


def test_correct_attempt_updates_bkt():
    from copy import deepcopy

    from app.db.connection import DEFAULT_MEMORY

    mem: dict = {}

    def get_memory(uid: str):
        return deepcopy(mem.get(uid, DEFAULT_MEMORY))

    def save_memory(uid: str, data):
        mem[uid] = data

    svc = MasteryService()
    svc.store.get_memory = get_memory
    svc.store.save_memory = save_memory
    graph = MagicMock()
    graph.write_learner_memory = MagicMock()
    graph.update_concept_mastery_on_graph = MagicMock()
    graph._find_chapter_node = MagicMock(return_value="Mechanics")
    graph.G = MagicMock()
    graph.G.__contains__ = MagicMock(return_value=False)

    evidence = AttemptEvidence(
        user_id="test-user-bkt",
        question_id="q1",
        concept_ids=["Mechanics"],
        is_correct=True,
        hints_used=0,
        max_hint_level=1,
        subject="Physics",
        chapter="Mechanics",
    )
    results = svc.record_attempt(evidence, graph)
    assert len(results) == 1
    assert results[0].p_known_after > results[0].p_known_before

    memory = mem["test-user-bkt"]
    assert memory["bkt_states"]["Mechanics"]["attempt_count"] == 1


def test_hint_heavy_attempt_lower_gain():
    engine = BKTEngine()
    state_light = ConceptBKTState(concept_id="c1")
    state_heavy = ConceptBKTState(concept_id="c2")
    w_light = engine.evidence_weight(hints_used=0, max_hint_level=1, solution_revealed=False)
    w_heavy = engine.evidence_weight(hints_used=3, max_hint_level=3, solution_revealed=False)
    r_light = engine.update(state_light, is_correct=True, evidence_weight=w_light, practised_at="2026-01-01T00:00:00+00:00")
    r_heavy = engine.update(state_heavy, is_correct=True, evidence_weight=w_heavy, practised_at="2026-01-01T00:00:00+00:00")
    assert r_light.delta > r_heavy.delta


def test_weak_concept_scheduled_for_review():
    scheduler = RevisionScheduler()
    state = ConceptBKTState(concept_id="WeakTopic", p_known=0.3)
    item = scheduler.schedule("WeakTopic", state, subject="Chemistry", is_correct=False)
    assert item is not None
    assert item.reason == "weak_concept_priority"
    assert state.next_review_at is not None


def test_next_question_recommendation_explainable():
    selector = AdaptiveQuestionSelector()
    states = {"Mechanics": ConceptBKTState(concept_id="Mechanics", p_known=0.5)}
    q = {
        "question_id": "q_mechanics_1",
        "subject": "Physics",
        "chapter": "Mechanics",
        "difficulty": "Medium",
        "review_status": "REVIEWED",
    }
    rec = selector.score_question(q, states, ["Mechanics"], revision_targets={"Mechanics"})
    assert rec.score > 0
    assert len(rec.reasons) >= 2
    assert any("revision" in r or "proximal" in r for r in rec.reasons)


@pytest.mark.asyncio
async def test_orchestrator_no_mastery_on_greeting():
    mock = MockModelGateway("Hello!")
    orchestrator = TutorOrchestrator(model_gateway=mock)
    graph = MagicMock()
    graph.get_graph_rag_context.return_value = {}
    graph.get_questions_by_concept.return_value = {}
    graph.write_learner_memory = MagicMock()
    graph.update_concept_mastery_on_graph = MagicMock()
    retrieval = MagicMock()
    retrieval.ready = False
    verification = VerificationService()
    app_state = SimpleNamespace(graph=graph, retrieval=retrieval, verification=verification)

    ctx = TutorContext(
        user_id="u-greet",
        student_message="Hello!",
        learner_memory={"mastery": {"X": 0.5}, "misconceptions": {}, "session_history": [], "hint_levels": {}},
    )
    mastery_before = ctx.learner_memory["mastery"]["X"]
    events = []
    async for event in orchestrator.handle_message(ctx, app_state):
        events.append(event)
    assert ctx.learner_memory["mastery"]["X"] == mastery_before
    mastery_events = [e for e in events if e.get("type") == "pipeline_step" and e.get("step") == "mastery_update"]
    assert not mastery_events
