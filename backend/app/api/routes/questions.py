import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import CurrentUser, get_current_user
from app.services.corpus import get_questions_ram
from app.services.questions import build_question_lookup, practice_question_pool, resolve_question

router = APIRouter()
logger = logging.getLogger("tutor.api")


@router.get("/questions")
async def get_questions(
    subject: Optional[str] = None,
    chapter: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10000, ge=1, le=10000),
    practice_ready: bool = False,
):
    """In-memory filtering and chunked pagination over the question corpus."""
    logger.debug(
        "GET /questions — subject=%r, chapter=%r, page=%s, limit=%s",
        subject,
        chapter,
        page,
        limit,
    )

    questions_ram = get_questions_ram()
    if practice_ready:
        questions_ram = practice_question_pool(questions_ram)
    filtered = questions_ram
    if subject:
        filtered = [q for q in filtered if q.get("subject", "").lower() == subject.lower()]
    if chapter and chapter.lower() != "all chapters":
        filtered = [q for q in filtered if q.get("chapter", "").lower() == chapter.lower()]

    filtered.sort(
        key=lambda x: (
            x.get("subject", ""),
            int(x.get("year") or 0),
            {"Easy": 1, "Medium": 2, "Hard": 3}.get(x.get("difficulty"), 4),
        )
    )

    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    result = filtered[start_idx:end_idx]

    logger.debug("  → Returning %s of %s filtered questions.", len(result), len(filtered))
    return {
        "total_matches": len(filtered),
        "page": page,
        "limit": limit,
        "questions": result,
    }


@router.get("/questions/{question_id}/similar")
async def get_similar_questions(
    request: Request,
    question_id: str,
    top_k: int = Query(3, ge=1, le=10),
    user: CurrentUser = Depends(get_current_user),
):
    """Return similar previous-year questions using hybrid FAISS+FTS5 retrieval."""
    retrieval = request.app.state.retrieval
    if not getattr(retrieval, "ready", False):
        return {"question_id": question_id, "results": [], "index_ready": False}

    questions_ram = get_questions_ram()
    lookup = build_question_lookup(questions_ram)
    source = resolve_question(question_id, questions_ram, retrieval, lookup)
    if not source:
        return {"question_id": question_id, "results": [], "index_ready": True}

    subject = source.get("subject")
    chapter = source.get("chapter")
    query_text = (
        source.get("stem_text")
        or source.get("normalized_text")
        or source.get("raw_text")
        or ""
    )[:400].strip()
    if not query_text:
        return {"question_id": question_id, "results": [], "index_ready": True}

    # Fetch one extra so we can drop the source question if it surfaces
    raw_results = await asyncio.to_thread(
        retrieval.search,
        query_text,
        subject=subject,
        chapter=chapter,
        top_k=top_k + 1,
    )

    results = []
    for hit in raw_results:
        hit_id = hit.get("question_id")
        if hit_id == question_id:
            continue
        # Resolve the full question so the frontend has stem + options + answer
        full = resolve_question(hit_id, questions_ram, retrieval, lookup) or {}
        results.append({
            "question_id": hit_id,
            "year": full.get("year") or hit.get("year"),
            "exam_type": full.get("exam_type") or full.get("paper_filename", ""),
            "subject": hit.get("subject"),
            "chapter": hit.get("chapter"),
            "topic": hit.get("topic"),
            "difficulty": full.get("difficulty") or "Medium",
            "stem_text": (
                full.get("stem_text")
                or full.get("normalized_text")
                or hit.get("stem_text")
                or ""
            ),
            "options": full.get("options") or [],
            "correct_answer": full.get("correct_answer"),
            "rrf_score": hit.get("rrf_score"),
        })
        if len(results) >= top_k:
            break

    return {"question_id": question_id, "results": results, "index_ready": True}


@router.get("/chapters")
async def get_chapters(request: Request):
    """Returns predefined canonical chapters grouped by subject from the Knowledge Graph."""
    logger.debug("GET /chapters")
    buckets: dict = {"Physics": [], "Chemistry": [], "Mathematics": []}
    for node, data in request.app.state.graph.G.nodes(data=True):
        if data.get("type") == "chapter":
            subj = data.get("subject", "General")
            if subj in buckets:
                buckets[subj].append(node)

    for k in buckets:
        buckets[k].sort()
    return buckets
