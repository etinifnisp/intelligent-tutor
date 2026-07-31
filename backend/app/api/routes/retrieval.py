import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/retrieval", tags=["retrieval"])
logger = logging.getLogger("tutor.retrieval.api")


@router.get("/search")
async def search_questions(
    request: Request,
    q: str = Query(..., min_length=2),
    subject: Optional[str] = None,
    chapter: Optional[str] = None,
    question_id: Optional[str] = None,
    top_k: int = Query(5, ge=1, le=20),
    user: CurrentUser = Depends(get_current_user),
):
    svc = request.app.state.retrieval
    if not svc.ready:
        return {"results": [], "error": "Retrieval indexes not built"}
    results = await asyncio.to_thread(
        svc.search, q, subject=subject, chapter=chapter, question_id=question_id, top_k=top_k
    )
    return {"query": q, "count": len(results), "results": results}
