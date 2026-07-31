import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import ws_authenticate
from app.learning.schemas import AttemptEvidence
from app.models.schemas import ChatPayload
from app.services.corpus import get_questions_ram
from app.tutor.orchestrator import TutorOrchestrator
from app.tutor.schemas import TutorContext, TutorIntent

router = APIRouter()
logger_ws = logging.getLogger("tutor.websocket")
_message_started: dict[str, float] = {}


def _resolve_context(payload: ChatPayload, websocket: WebSocket, user_id: str) -> TutorContext:
    questions_ram = get_questions_ram()
    orchestrator: TutorOrchestrator = websocket.app.state.orchestrator
    retrieval_svc = websocket.app.state.retrieval

    target_q = orchestrator.resolve_question(payload.question_id, questions_ram, retrieval_svc)
    active_chapter = "General"
    active_subject = ""

    if target_q:
        active_chapter = target_q.get("chapter", "General")
        active_subject = target_q.get("subject", "")

    active_concept_node = None
    if payload.question_id and payload.question_id in websocket.app.state.graph.G:
        for _, tgt, d in websocket.app.state.graph.G.out_edges(payload.question_id, data=True):
            if d.get("type") == "tests_concept":
                active_concept_node = tgt
                break

    if not active_concept_node:
        active_concept_node = (
            websocket.app.state.graph._find_chapter_node(active_chapter, active_subject)
            or active_chapter
        )

    if payload.chapter_context and not target_q:
        parts = payload.chapter_context.split(":", 1)
        if len(parts) == 2:
            active_subject = parts[0].strip()
            active_chapter = parts[1].strip()
        else:
            active_chapter = payload.chapter_context.strip()

    learner_memory = websocket.app.state.graph.get_learner_memory(user_id)

    return TutorContext(
        user_id=user_id,
        student_message=payload.student_message,
        question_id=payload.question_id,
        chapter_context=payload.chapter_context,
        chat_history=payload.chat_history,
        target_question=target_q,
        active_chapter=active_chapter,
        active_subject=active_subject,
        active_concept_node=active_concept_node,
        learner_memory=learner_memory,
    )


@router.websocket("/tutor/chat")
async def websocket_tutor_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_host = websocket.client.host if websocket.client else "unknown"
    try:
        user = await ws_authenticate(websocket)
    except WebSocketDisconnect:
        return
    user_id = user.id
    logger_ws.info("WebSocket connected from %s user=%s", client_host, user_id)

    conv_store = websocket.app.state.conversation_store
    orchestrator: TutorOrchestrator = websocket.app.state.orchestrator
    mastery_svc = websocket.app.state.mastery
    conversation_id = None

    try:
        while True:
            started = time.monotonic()
            raw_data = await websocket.receive_text()
            data_dict = json.loads(raw_data)
            payload = ChatPayload(**data_dict)

            logger_ws.info(
                "[%s] Message received — q_id=%s, history=%s turns, msg='%s...'",
                user_id,
                payload.question_id or "none",
                len(payload.chat_history),
                payload.student_message[:60],
            )

            conversation_id = conv_store.get_or_create(user_id, payload.question_id)
            conv_store.add_message(conversation_id, "user", payload.student_message)

            ctx = _resolve_context(payload, websocket, user_id)
            full_response = ""
            tutor_meta = None

            async for event in orchestrator.handle_message(ctx, websocket.app.state):
                if event["type"] == "token":
                    full_response += event.get("text", "")
                elif event["type"] == "tutor_meta":
                    tutor_meta = event.get("data")
                await websocket.send_json(event)

            if conversation_id and full_response:
                meta = tutor_meta or {}
                conv_store.add_message(
                    conversation_id,
                    "assistant",
                    full_response[:4000],
                    model_name=meta.get("model_name"),
                    prompt_version=meta.get("prompt_version"),
                    verification_status=meta.get("verification_status"),
                )

            response_time_ms = payload.response_time_ms
            if response_time_ms is None:
                response_time_ms = int((time.monotonic() - started) * 1000)

            msg_lower = payload.student_message.lower()
            is_answer_attempt = payload.question_id and (
                tutor_meta
                and tutor_meta.get("intent") == TutorIntent.ANSWER_CHECK.value
                or any(
                    w in msg_lower
                    for w in ("correct", "right answer", "is it correct", "is this right", "option")
                )
            )

            if is_answer_attempt and tutor_meta:
                vstatus = tutor_meta.get("verification_status")
                is_correct = None
                if vstatus == "VERIFIED":
                    is_correct = True
                elif vstatus == "INCORRECT":
                    is_correct = False

                if is_correct is not None:
                    hint_levels = ctx.learner_memory.get("hint_levels", {})
                    max_hint = int(hint_levels.get(payload.question_id or "_general", 1))
                    hints_used = max(0, max_hint - 1)
                    solution_revealed = tutor_meta.get("pedagogy_mode") == "SOLVE"

                    concepts = mastery_svc.resolve_concepts(
                        websocket.app.state.graph,
                        payload.question_id,
                        ctx.active_chapter,
                        ctx.active_subject,
                    )

                    evidence = AttemptEvidence(
                        user_id=user_id,
                        question_id=payload.question_id,
                        concept_ids=concepts,
                        is_correct=is_correct,
                        hints_used=hints_used,
                        max_hint_level=max_hint,
                        response_time_ms=response_time_ms,
                        confidence_before=payload.confidence_before,
                        solution_revealed=solution_revealed,
                        subject=ctx.active_subject,
                        chapter=ctx.active_chapter,
                        difficulty=(ctx.target_question or {}).get("difficulty", "Medium"),
                    )

                    updates = mastery_svc.record_attempt(evidence, websocket.app.state.graph)
                    if updates:
                        await websocket.send_json(
                            {
                                "type": "pipeline_step",
                                "step": "mastery_update",
                                "data": {
                                    "source": "bkt_attempt",
                                    "updates": [u.model_dump() for u in updates],
                                },
                            }
                        )

                    misconception = None
                    if not is_correct:
                        misconception = mastery_svc.misconceptions.classify(evidence)

                    conv_store.record_attempt(
                        user_id,
                        payload.question_id,
                        answer=payload.student_message,
                        is_correct=is_correct,
                        confidence=payload.confidence_before,
                        hints_used=hints_used,
                        max_hint_level=max_hint,
                        response_time_ms=response_time_ms,
                        solution_revealed=solution_revealed,
                        concept_ids=concepts,
                        misconception_type=misconception,
                    )

    except WebSocketDisconnect:
        logger_ws.info("WebSocket cleanly disconnected from %s.", client_host)
    except Exception as e:
        logger_ws.error("Internal error in WebSocket handler: %s", e, exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": "Internal server error. Please retry."})
        except Exception:
            pass
