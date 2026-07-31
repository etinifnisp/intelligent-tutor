"""Learning API — mastery, revision, adaptive recommendations."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import CurrentUser, get_current_user
from app.learning.schemas import ConceptBKTState
from app.services.corpus import get_questions_ram
from app.services.questions import (
    build_question_lookup,
    practice_question_pool,
    question_pool,
    resolve_question,
)

router = APIRouter(prefix="/learning", tags=["learning"])
logger = logging.getLogger("tutor.learning.api")


def _enrich_mistake(row: dict, request: Request, lookup: dict[str, dict]) -> dict:
    q = resolve_question(row.get("question_id"), get_questions_ram(), request.app.state.retrieval, lookup) or {}
    text = q.get("raw_text") or q.get("stem_text") or q.get("normalized_text") or ""
    return {
        **row,
        "subject": q.get("subject", ""),
        "chapter": q.get("chapter", ""),
        "difficulty": q.get("difficulty", ""),
        "question_text": text[:500],
        "correct_answer": q.get("correct_answer"),
        "images": q.get("images", []),
    }


@router.get("/mastery/me")
async def get_my_mastery(request: Request, user: CurrentUser = Depends(get_current_user)):
    memory = request.app.state.mastery.store.get_memory(user.id)
    memory = request.app.state.mastery.sync_mastery_display(memory)
    return {
        "user_id": user.id,
        "mastery": memory.get("mastery", {}),
        "bkt_states": memory.get("bkt_states", {}),
        "misconceptions": memory.get("misconceptions", {}),
    }


@router.get("/revision/me")
async def get_my_revision(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    subject: Optional[str] = None,
):
    items = request.app.state.mastery.get_revision_schedule(user.id, subject=subject or "")
    return {"user_id": user.id, "due": [i.model_dump() for i in items]}


@router.get("/next-question")
async def get_next_question(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    subject: Optional[str] = None,
    limit: int = Query(5, ge=1, le=20),
):
    retrieval = request.app.state.retrieval
    pool = practice_question_pool(get_questions_ram())

    recs = request.app.state.mastery.recommend_questions(
        user.id,
        pool,
        request.app.state.graph,
        subject=subject or "",
        limit=limit,
    )
    enriched = []
    lookup = build_question_lookup(pool)
    for rec in recs:
        payload = rec.model_dump()
        q = resolve_question(rec.question_id, pool, retrieval, lookup) or {}
        payload["question"] = q
        enriched.append(payload)
    return {
        "user_id": user.id,
        "recommendations": enriched,
    }


@router.get("/summary/me")
async def get_my_summary(request: Request, user: CurrentUser = Depends(get_current_user)):
    summary = request.app.state.mastery.build_summary(user.id)
    return summary.model_dump()


@router.get("/today/me")
async def get_today_plan(request: Request, user: CurrentUser = Depends(get_current_user)):
    mastery_svc = request.app.state.mastery
    summary = mastery_svc.build_summary(user.id)
    due = mastery_svc.get_revision_schedule(user.id)
    retrieval = request.app.state.retrieval
    pool = question_pool(get_questions_ram(), retrieval)
    recs = mastery_svc.recommend_questions(
        user.id, pool, request.app.state.graph, limit=3
    )

    weak = summary.weak_concepts[:3]
    session_minutes = 20
    questions_target = max(3, min(8, len(due) + len(weak)))

    return {
        "user_id": user.id,
        "session_minutes": session_minutes,
        "questions_target": questions_target,
        "revision_due_count": len(due),
        "revision_due": [d.model_dump() for d in due[:5]],
        "weak_concepts": weak,
        "narrative": summary.narrative,
        "recommended_questions": [r.model_dump() for r in recs],
        "total_attempts": summary.total_attempts,
    }


@router.get("/mistakes/me")
async def get_my_mistakes(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=50),
):
    conv_store = request.app.state.conversation_store
    mastery_svc = request.app.state.mastery
    rows = conv_store.get_recent_mistakes(user.id, limit=limit)
    lookup = build_question_lookup(get_questions_ram())
    mistakes = [_enrich_mistake(r, request, lookup) for r in rows]

    retry_pool = []
    if mistakes:
        retrieval = request.app.state.retrieval
        pool = question_pool(get_questions_ram(), retrieval)
        concept = mistakes[0].get("concept_ids", [None])[0]
        if concept:
            recs = mastery_svc.recommend_questions(
                user.id, pool, request.app.state.graph, limit=3
            )
            retry_pool = [r.model_dump() for r in recs]

    return {
        "user_id": user.id,
        "mistakes": mistakes,
        "retry_recommendations": retry_pool,
    }


@router.get("/progress/me")
async def get_my_progress(request: Request, user: CurrentUser = Depends(get_current_user)):
    mastery_svc = request.app.state.mastery
    conv_store = request.app.state.conversation_store
    memory = mastery_svc.sync_mastery_display(mastery_svc.store.get_memory(user.id))
    states = {
        cid: ConceptBKTState(**raw) for cid, raw in memory.get("bkt_states", {}).items()
    }
    attempt_metrics = conv_store.get_progress_metrics(user.id)
    due = mastery_svc.get_revision_schedule(user.id)

    concept_rows = []
    for cid, state in states.items():
        acc = state.correct_count / state.attempt_count if state.attempt_count else 0.0
        no_hint_acc = (
            state.correct_without_hints / state.attempt_count if state.attempt_count else 0.0
        )
        concept_rows.append({
            "concept_id": cid,
            "p_known": round(state.p_known, 3),
            "attempt_count": state.attempt_count,
            "accuracy": round(acc, 3),
            "accuracy_without_hints": round(no_hint_acc, 3),
            "mastered": state.evidence_sufficient,
            "subject": memory.get("concept_subjects", {}).get(cid, ""),
        })

    concept_rows.sort(key=lambda x: x["p_known"])
    strongest = [c for c in reversed(concept_rows) if c["attempt_count"] > 0][:5]
    weakest = [c for c in concept_rows if c["attempt_count"] > 0][:5]

    revision_total = len(memory.get("revision_queue", []))
    revision_due = len(due)
    revision_completed = max(0, revision_total - revision_due)

    return {
        "user_id": user.id,
        "concepts": concept_rows,
        "strongest": strongest,
        "weakest": weakest,
        "misconceptions": memory.get("misconceptions", {}),
        "revision_due": revision_due,
        "revision_completed": revision_completed,
        **attempt_metrics,
    }
