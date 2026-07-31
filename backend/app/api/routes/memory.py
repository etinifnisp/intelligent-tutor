import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import CurrentUser, get_current_user
from app.services.learner_stats import build_learner_stats

router = APIRouter()
logger = logging.getLogger("tutor.api")


def _assert_owner(user: CurrentUser, target_user_id: str) -> None:
    if not user.owns(target_user_id):
        raise HTTPException(status_code=403, detail="Access denied")


@router.get("/memory/me")
async def get_my_memory(request: Request, user: CurrentUser = Depends(get_current_user)):
    logger.debug("GET /memory/me user=%s", user.id)
    return request.app.state.graph.get_learner_memory(user.id)


@router.get("/stats/me")
async def get_my_stats(request: Request, user: CurrentUser = Depends(get_current_user)):
    logger.debug("GET /stats/me user=%s", user.id)
    return build_learner_stats(user.id, request)


@router.get("/adaptive/me")
async def get_my_adaptive_path(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    subject: Optional[str] = None,
):
    logger.debug("GET /adaptive/me user=%s subject=%s", user.id, subject)
    return {
        "user_id": user.id,
        "next_concept": request.app.state.graph.get_adaptive_next_concept(
            user.id, subject or ""
        ),
    }


# Legacy routes — require auth and enforce ownership (no arbitrary session IDs)
@router.get("/memory/{session_id}")
async def get_learner_dashboard_memory(
    session_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    _assert_owner(user, session_id)
    return request.app.state.graph.get_learner_memory(session_id)


@router.get("/stats/{session_id}")
async def get_learner_stats(
    session_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    _assert_owner(user, session_id)
    return build_learner_stats(session_id, request)


@router.get("/adaptive/{session_id}")
async def get_adaptive_path(
    session_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    subject: Optional[str] = None,
):
    _assert_owner(user, session_id)
    return {
        "session_id": session_id,
        "next_concept": request.app.state.graph.get_adaptive_next_concept(
            session_id, subject or ""
        ),
    }
