"""Model failure and timeout resilience tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.tutor.model_gateway import FailingModelGateway, MockModelGateway, TimeoutModelGateway
from app.tutor.orchestrator import TutorOrchestrator
from app.tutor.schemas import TutorContext


@pytest.mark.asyncio
async def test_failing_model_gateway_raises():
    gw = FailingModelGateway()
    with pytest.raises(RuntimeError, match="Simulated model failure"):
        async for _ in gw.generate_stream("sys", [{"role": "user", "content": "hi"}]):
            pass


@pytest.mark.asyncio
async def test_timeout_gateway_raises_on_slow_stream():
  async def slow_stream(*_args, **_kwargs):
      await asyncio.sleep(5)
      yield "late"

  inner = MagicMock()
  inner.generate_stream = slow_stream
  gw = TimeoutModelGateway(inner, timeout_s=0.05)
  with pytest.raises(TimeoutError):
      async for _ in gw.generate_stream("sys", [{"role": "user", "content": "hi"}]):
          pass


@pytest.mark.asyncio
async def test_orchestrator_survives_model_failure():
    from app.verification.service import VerificationService

    orchestrator = TutorOrchestrator(model_gateway=FailingModelGateway())
    ctx = TutorContext(
        user_id="u-test",
        student_message="Explain Newton's first law",
        learner_memory={"mastery": {}, "misconceptions": {}, "session_history": [], "hint_levels": {}},
    )
    graph = MagicMock()
    graph.get_graph_rag_context.return_value = {
        "active_concept": "Mechanics",
        "current_mastery": 0.4,
        "prereq_chain": [],
        "unmastered_prereqs": [],
        "hint_scaffolds": [],
        "graph_hint": "",
    }
    graph.get_questions_by_concept.return_value = []
    app_state = SimpleNamespace(
        retrieval=SimpleNamespace(
            ready=False,
            search=lambda *a, **k: [],
            format_evidence_block=lambda e: "",
            concept_note=lambda *a: None,
        ),
        verification=VerificationService(),
        graph=graph,
    )

    events = []
    async for event in orchestrator.handle_message(ctx, app_state):
        events.append(event)

    assert any(e["type"] == "token" for e in events)
    assert any(e["type"] in {"done", "tutor_meta"} for e in events)


@pytest.mark.asyncio
async def test_mock_model_gateway_streams():
    gw = MockModelGateway("Hello world")
    chunks = []
    async for token in gw.generate_stream("sys", [{"role": "user", "content": "hi"}]):
        chunks.append(token)
    assert "".join(chunks) == "Hello world"
