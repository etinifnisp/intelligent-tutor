import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import CurrentUser, get_current_user
from app.models.schemas import (
    GuestConvertRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import (
    create_guest_user,
    login_user,
    refresh_access_token,
    register_user,
    upgrade_guest_to_student,
)
from app.services.learner_store import LearnerStore

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("tutor.auth")


@router.post("/guest", response_model=TokenResponse)
async def create_guest():
    """Anonymous guest session with server-issued identity."""
    result = create_guest_user()
    logger.info("Guest user created: %s", result["user"]["id"])
    return result


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, request: Request):
    try:
        result = register_user(
            body.username,
            body.password,
            role="STUDENT",
            migrate_from_user_id=body.migrate_from_user_id,
        )
    except ValueError as exc:
        if str(exc) == "username_taken":
            raise HTTPException(status_code=409, detail="Username already taken") from exc
        raise
    if body.migrate_from_user_id:
        store: LearnerStore = request.app.state.learner_store
        store.migrate_memory(body.migrate_from_user_id, result["user"]["id"])
        logger.info(
            "Migrated learner data %s -> %s",
            body.migrate_from_user_id,
            result["user"]["id"],
        )
    return result


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    result = login_user(body.username, body.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return result


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    result = refresh_access_token(body.refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return result


@router.get("/me")
async def me(user: CurrentUser = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}


@router.post("/convert-guest", response_model=TokenResponse)
async def convert_guest(
    body: GuestConvertRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Upgrade current guest account to a registered student (keeps progress)."""
    result = upgrade_guest_to_student(user.id, body.username, body.password)
    if not result:
        raise HTTPException(status_code=409, detail="Username taken or account not a guest")
    return result
