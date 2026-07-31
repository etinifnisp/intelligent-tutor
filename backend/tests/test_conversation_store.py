"""Conversation store and attempt metrics tests."""

from __future__ import annotations

from app.services.auth_service import create_guest_user
from app.services.conversation_store import ConversationStore


def test_record_and_fetch_mistakes():
    store = ConversationStore()
    user_id = create_guest_user()["user"]["id"]
    qid = "q_test_1"

    store.record_attempt(
        user_id,
        qid,
        answer="option A",
        is_correct=False,
        confidence=0.8,
        hints_used=1,
        max_hint_level=2,
        response_time_ms=12000,
        misconception_type="careless_mistake",
        concept_ids=["Mechanics"],
    )
    store.record_attempt(
        user_id,
        qid,
        answer="option B",
        is_correct=True,
        confidence=0.6,
        hints_used=0,
        max_hint_level=0,
        response_time_ms=8000,
    )

    mistakes = store.get_recent_mistakes(user_id)
    assert len(mistakes) == 1
    assert mistakes[0]["answer"] == "option A"
    assert mistakes[0]["misconception_type"] == "careless_mistake"

    metrics = store.get_progress_metrics(user_id)
    assert metrics["total_attempts"] == 2
    assert metrics["accuracy"] == 0.5
    assert metrics["accuracy_without_hints"] == 0.5
