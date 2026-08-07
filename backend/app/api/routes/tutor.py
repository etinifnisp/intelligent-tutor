import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.api.deps import negotiated_ws_subprotocol, ws_authenticate
from app.config import MAX_MESSAGE_LENGTH, MODEL_NAME, get_openrouter_api_key, using_openrouter
from app.learning.schemas import AttemptEvidence
from app.middleware.rate_limit import allow_request
from app.models.schemas import ChatPayload
from app.services.corpus import get_questions_ram
from app.services.model_catalog import list_allowed_models, resolve_openrouter_model
from app.tutor.model_gateway import create_model_gateway
from app.tutor.orchestrator import TutorOrchestrator
from app.tutor.schemas import TutorContext, TutorIntent

router = APIRouter()
logger_ws = logging.getLogger("tutor.websocket")


@router.get("/tutor/models")
async def list_tutor_models():
    return {
        "provider": "openrouter" if using_openrouter() else "gemini",
        "default_model": resolve_openrouter_model(MODEL_NAME),
        "models": list_allowed_models(),
    }


def _build_model_gateway(payload: ChatPayload):
    api_key = get_openrouter_api_key()
    if not api_key:
        return None
    model_id = payload.resolved_openrouter_model()
    return create_model_gateway(
        provider="openrouter",
        api_key=api_key,
        model_name=model_id,
    )


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


async def _process_message(
    websocket: WebSocket,
    payload: ChatPayload,
    user_id: str,
    *,
    conversation_id: str | None,
) -> str | None:
    conv_store = websocket.app.state.conversation_store
    orchestrator: TutorOrchestrator = websocket.app.state.orchestrator
    mastery_svc = websocket.app.state.mastery

    conv_store.add_message(conversation_id, "user", payload.student_message)

    ctx = _resolve_context(payload, websocket, user_id)
    full_response = ""
    tutor_meta = None
    done_sent = False

    model_override = _build_model_gateway(payload)
    if model_override:
        active_model_name = getattr(getattr(model_override, "inner", None), "model_name", MODEL_NAME)
        logger_ws.info("[%s] Using OpenRouter gateway (model=%s)", user_id, active_model_name)
    elif not get_openrouter_api_key():
        logger_ws.warning("[%s] OPENROUTER_API_KEY missing — using server default model gateway", user_id)

    try:
        async for event in orchestrator.handle_message(ctx, websocket.app.state, model_gateway=model_override):
            if event["type"] == "token":
                full_response += event.get("text", "")
            elif event["type"] == "tutor_meta":
                tutor_meta = event.get("data")
            elif event["type"] == "done":
                done_sent = True
            await websocket.send_json(event)
    except Exception as exc:
        logger_ws.error("Tutor pipeline failed for %s: %s", user_id, exc, exc_info=True)
        await websocket.send_json(
            {"type": "error", "message": "Tutor is taking too long or hit an error. Please retry."}
        )
        if not done_sent:
            await websocket.send_json({"type": "done"})
        return conversation_id

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
        response_time_ms = 0

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

    return conversation_id


@router.websocket("/tutor/chat")
async def websocket_tutor_endpoint(websocket: WebSocket):
    client_host = websocket.client.host if websocket.client else "unknown"
    negotiated = negotiated_ws_subprotocol(websocket)
    await websocket.accept(subprotocol=negotiated)
    try:
        user = await ws_authenticate(websocket)
    except WebSocketDisconnect:
        return
    user_id = user.id
    logger_ws.info("WebSocket connected from %s user=%s", client_host, user_id)

    conv_store = websocket.app.state.conversation_store
    conversation_id = None

    try:
        while True:
            raw_data = await websocket.receive_text()
            if len(raw_data) > MAX_MESSAGE_LENGTH * 4:
                await websocket.send_json(
                    {"type": "error", "message": "Message too large. Please shorten your request."}
                )
                await websocket.send_json({"type": "done"})
                continue

            try:
                data_dict = json.loads(raw_data)
                payload = ChatPayload(**data_dict)
            except (json.JSONDecodeError, ValidationError):
                await websocket.send_json(
                    {"type": "error", "message": "Invalid message format. Please retry."}
                )
                await websocket.send_json({"type": "done"})
                continue

            if not allow_request(f"ws:{user_id}", limit=30, window_seconds=60):
                await websocket.send_json(
                    {"type": "error", "message": "Too many tutor requests. Please wait a moment."}
                )
                await websocket.send_json({"type": "done"})
                continue

            logger_ws.info(
                "[%s] Message received — q_id=%s, history=%s turns, msg='%s...'",
                user_id,
                payload.question_id or "none",
                len(payload.chat_history),
                payload.student_message[:60],
            )

            conversation_id = conv_store.get_or_create(user_id, payload.question_id)
            started = time.monotonic()
            conversation_id = await _process_message(
                websocket,
                payload,
                user_id,
                conversation_id=conversation_id,
            )
            if payload.response_time_ms is None:
                _ = started  # timing captured inside orchestrator events when needed

    except WebSocketDisconnect:
        logger_ws.info("WebSocket cleanly disconnected from %s.", client_host)
    except Exception as e:
        logger_ws.error("Internal error in WebSocket handler: %s", e, exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": "Internal server error. Please retry."})
            await websocket.send_json({"type": "done"})
        except Exception:
            pass
