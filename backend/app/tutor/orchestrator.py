"""Tutor orchestrator — controlled tutoring workflow."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from app.verification.text_utils import response_reveals_answer
from app.tutor.model_gateway import ModelGateway, create_model_gateway
from app.tutor.pedagogy import PedagogyPolicy
from app.tutor.prompts import PROMPT_VERSION, build_chat_contents, build_system_prompt
from app.tutor.router import IntentRouter
from app.services.questions import resolve_question
from app.tutor.schemas import (
    IntentClassification,
    NextAction,
    PedagogyMode,
    TutorContext,
    TutorIntent,
    TutorResponse,
    VerificationStatus,
)
from app.verification.answer_checker import get_official_answer
from app.verification.schemas import VerificationReport

logger = logging.getLogger("tutor.orchestrator")


class TutorOrchestrator:
    def __init__(self, model_gateway: ModelGateway | None = None) -> None:
        self.router = IntentRouter()
        self.pedagogy = PedagogyPolicy()
        self.model = model_gateway or create_model_gateway()

    def resolve_question(
        self,
        question_id: Optional[str],
        questions_ram: list[dict],
        retrieval_svc: Any,
    ) -> Optional[dict]:
        return resolve_question(question_id, questions_ram, retrieval_svc)

    def classify(self, ctx: TutorContext) -> IntentClassification:
        return self.router.classify(ctx.student_message, has_question=bool(ctx.target_question))

    async def handle_message(self, ctx: TutorContext, app_state: Any) -> AsyncIterator[dict]:
        """Yield WebSocket-compatible events with structured tutor metadata."""
        classification = self.classify(ctx)
        yield {
            "type": "status",
            "lane": classification.lane,
            "message": f"Routing to {classification.lane} cluster...",
        }
        yield {
            "type": "pipeline_step",
            "step": "intent_classify",
            "data": {
                "intent": classification.intent.value,
                "lane": classification.lane,
                "pedagogy_mode": classification.pedagogy_mode.value,
                "requires_retrieval": classification.requires_retrieval,
                "confidence": classification.confidence,
                "message_preview": ctx.student_message[:80],
            },
        }

        graph_ctx: dict = {}
        related_questions: dict = {}
        if classification.requires_retrieval:
            graph_ctx = app_state.graph.get_graph_rag_context(
                session_id=ctx.user_id,
                chapter=ctx.active_chapter,
                subject=ctx.active_subject,
            )
            yield {
                "type": "pipeline_step",
                "step": "graph_query",
                "data": {
                    "concept": graph_ctx.get("active_concept"),
                    "mastery": round(graph_ctx.get("current_mastery", 0), 2),
                    "prereq_chain": graph_ctx.get("prereq_chain", []),
                    "unmastered_prereqs": [
                        u["concept"] for u in graph_ctx.get("unmastered_prereqs", [])
                    ],
                    "hint_scaffolds": graph_ctx.get("hint_scaffolds", []),
                    "scaffolding": graph_ctx.get("graph_hint", "")[:200],
                },
            }
            related_questions = app_state.graph.get_questions_by_concept(
                ctx.active_chapter, ctx.active_subject, limit_per_difficulty=1
            )
            ctx.graph_ctx = graph_ctx
            ctx.related_questions = related_questions

        hint_level = self.pedagogy.get_hint_level(
            ctx.learner_memory, ctx.question_id, ctx.student_message
        )
        directive = self.pedagogy.select(
            classification,
            hint_level=hint_level,
            student_requested_solution=classification.intent == TutorIntent.FULL_SOLUTION,
        )

        yield {
            "type": "pipeline_step",
            "step": "pedagogy_select",
            "data": {
                "mode": directive.mode.value,
                "hint_level": directive.hint_level,
                "reveal_answer": directive.reveal_answer,
            },
        }

        evidence: list[dict] = []
        evidence_block = ""
        if classification.requires_retrieval and getattr(app_state.retrieval, "ready", False):
            search_query = ctx.student_message
            if ctx.target_question:
                search_query = (
                    ctx.target_question.get("stem_text")
                    or ctx.target_question.get("raw_text")
                    or ctx.target_question.get("chapter")
                    or search_query
                )
            evidence = await asyncio.to_thread(
                app_state.retrieval.search,
                search_query,
                subject=ctx.active_subject or None,
                chapter=ctx.active_chapter if ctx.active_chapter != "General" else None,
                question_id=ctx.question_id,
                top_k=5,
            )
            yield {
                "type": "pipeline_step",
                "step": "retrieval",
                "data": {
                    "count": len(evidence),
                    "question_ids": [e.get("question_id") for e in evidence],
                },
            }
            evidence_block = app_state.retrieval.format_evidence_block(evidence)
            note = app_state.retrieval.concept_note(ctx.active_subject, ctx.active_chapter)
            if note:
                evidence_block += f"\n\nConcept note: {note.get('note')}"

        # Determine answer key and diagram availability from active question + evidence.
        answer_available = bool(
            ctx.target_question and get_official_answer(ctx.target_question)
        )
        # diagram_missing: question references a diagram but we have no actual file.
        q_has_diagram = bool(ctx.target_question and ctx.target_question.get("diagram_paths"))
        evidence_has_missing_diagram = any(
            item.get("has_diagram") and not item.get("diagram_paths") for item in evidence
        )
        diagram_missing = (q_has_diagram and not any(
            ctx.target_question.get("diagram_paths", [])
        )) or evidence_has_missing_diagram

        mastery_map = ctx.learner_memory.get("mastery", {})
        misconceptions = ctx.learner_memory.get("misconceptions", {})
        safe_question = self.pedagogy.strip_answer_from_context(
            ctx.target_question, directive.reveal_answer
        )

        system_instruction = build_system_prompt(
            pedagogy_constraints=directive.system_constraints,
            pedagogy_mode=directive.mode.value,
            hint_level=directive.hint_level,
            mastery_map=mastery_map,
            misconceptions=misconceptions,
            graph_ctx=graph_ctx or None,
            evidence_block=evidence_block,
            question_context=safe_question,
            related_questions=related_questions or None,
            answer_available=answer_available,
            diagram_missing=diagram_missing,
        )

        contents = build_chat_contents(ctx.chat_history, ctx.student_message)

        verification_status = VerificationStatus.UNVERIFIED
        next_action = NextAction.CONTINUE
        attempt_report: VerificationReport | None = None
        answer_confidence = 0.0

        if classification.requires_verification or classification.intent == TutorIntent.ANSWER_CHECK:
            verifier = app_state.verification
            if not answer_available:
                # No answer key — skip deterministic checking to avoid misleading feedback.
                attempt_report = VerificationReport(
                    status=VerificationStatus.UNVERIFIED,
                    confidence=0.0,
                    summary="No verified answer key for this question — verification skipped.",
                )
                verification_status = VerificationStatus.UNVERIFIED
            else:
                attempt_report = verifier.verify_attempt(ctx.student_message, ctx.target_question)
                verification_status = VerificationStatus(attempt_report.status.value)
                answer_confidence = attempt_report.confidence
                if attempt_report.status.value == "VERIFIED":
                    next_action = NextAction.CONTINUE
                elif attempt_report.status.value == "INCORRECT":
                    next_action = NextAction.TRY_AGAIN
                elif attempt_report.status.value == "PENDING":
                    next_action = NextAction.TRY_AGAIN

            yield {
                "type": "pipeline_step",
                "step": "verification",
                "data": {
                    "phase": "attempt",
                    "status": attempt_report.status.value,
                    "confidence": attempt_report.confidence,
                    "summary": attempt_report.summary,
                    "tool_calls": [c.model_dump() for c in attempt_report.tool_calls],
                },
            }
            if attempt_report.summary and answer_available:
                system_instruction += f"\n\n== VERIFIED CHECK RESULT ==\n{attempt_report.summary}\n"

        full_response = ""
        model_name = type(self.model).__name__
        try:
            async for token in self.model.generate_stream(system_instruction, contents):
                full_response += token
                yield {"type": "token", "text": token}
        except Exception as exc:
            logger.error("Model generation failed: %s", exc, exc_info=True)
            from app.services.tutor_fallback import get_local_socratic_fallback

            full_response = get_local_socratic_fallback(
                ctx.target_question,
                ctx.student_message,
                ctx.active_concept_node,
                ctx.active_chapter,
                ctx.active_subject,
            )
            model_name = "local_fallback"
            chunk_size = 12
            for i in range(0, len(full_response), chunk_size):
                yield {"type": "token", "text": full_response[i : i + chunk_size]}

        response_report: VerificationReport | None = None
        if attempt_report or classification.requires_verification:
            verifier = app_state.verification
            response_report = verifier.verify_response(
                full_response,
                attempt_report,
                pedagogy_mode=directive.mode.value,
                hint_level=directive.hint_level,
                question=ctx.target_question,
                reveal_answer=directive.reveal_answer,
            )
            final_status, answer_confidence = verifier.merge_status(
                attempt_report or VerificationReport(status=verification_status, confidence=0.0),
                response_report,
            )
            verification_status = VerificationStatus(final_status.value)

            yield {
                "type": "pipeline_step",
                "step": "verification",
                "data": {
                    "phase": "response",
                    "status": response_report.status.value,
                    "confidence": response_report.confidence,
                    "summary": response_report.summary,
                    "checks_passed": response_report.checks_passed,
                    "checks_failed": response_report.checks_failed,
                },
            }

            if response_report.status.value == "CONFLICTING_SOURCE":
                full_response += (
                    "\n\n_(This explanation could not be fully verified against the answer key "
                    "and has been marked unverified.)_"
                )
                verification_status = VerificationStatus.UNVERIFIED

        correct = get_official_answer(ctx.target_question) if ctx.target_question else None

        if (
            directive.mode == PedagogyMode.HINT
            and not directive.reveal_answer
            and response_reveals_answer(full_response, str(correct).upper() if correct else None)
        ):
            verification_status = VerificationStatus.UNVERIFIED
            full_response += (
                "\n\n_(Hint sanitized: final answer withheld per pedagogy policy. "
                "Share your next step or ask for another hint.)_"
            )

        concepts = [ctx.active_concept_node] if ctx.active_concept_node else []
        tutor_response = TutorResponse(
            message=full_response,
            intent=classification.intent,
            verification_status=verification_status,
            hint_level=directive.hint_level,
            concepts=concepts,
            next_action=next_action,
            mastery_update_allowed=(
                classification.intent == TutorIntent.ANSWER_CHECK
                and verification_status == VerificationStatus.VERIFIED
            ),
            source_question_id=ctx.question_id,
            pedagogy_mode=directive.mode,
            prompt_version=PROMPT_VERSION,
            model_name=model_name,
            answer_confidence=round(answer_confidence, 3),
            verification_report={
                "attempt": attempt_report.model_dump() if attempt_report else None,
                "response": response_report.model_dump() if response_report else None,
            },
        )

        yield {
            "type": "pipeline_step",
            "step": "llm_complete",
            "data": {
                "model": model_name,
                "words": len(full_response.split()),
                "lane": classification.lane,
                "intent": classification.intent.value,
            },
        }

        delta, mastery_event = self._update_mastery(ctx, classification, tutor_response)
        if mastery_event:
            yield mastery_event

        ctx.learner_memory.setdefault("session_history", []).append(
            {
                "user": ctx.student_message,
                "ai": full_response[:500],
                "chapter": ctx.active_chapter,
                "intent": classification.intent.value,
                "lane": classification.lane,
                "timestamp": datetime.now().isoformat(),
            }
        )
        app_state.graph.write_learner_memory(ctx.user_id, ctx.learner_memory)

        yield {"type": "tutor_meta", "data": tutor_response.model_dump()}
        yield {"type": "done", "mastery_delta": delta}

    def _update_mastery(
        self,
        ctx: TutorContext,
        classification: IntentClassification,
        response: TutorResponse,
    ) -> tuple[float, Optional[dict]]:
        """Phase 7: mastery updates only via attempt events — no chat-signal deltas."""
        _ = classification, response
        return 0.0, None
