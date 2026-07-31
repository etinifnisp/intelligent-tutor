import logging
from typing import Optional

from fastapi import APIRouter, Query, Request

from app.services.corpus import get_questions_ram
from app.services.questions import practice_question_pool

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
