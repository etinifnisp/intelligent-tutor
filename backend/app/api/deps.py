"""FastAPI auth dependencies."""

from __future__ import annotations

from typing import Annotated, Optional

import jwt
from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth_service import decode_access_token, get_user_by_id

_bearer = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user_id: str, username: str, role: str):
        self.id = user_id
        self.username = username
        self.role = role

    def owns(self, resource_user_id: str) -> bool:
        if self.role in {"ADMIN", "TEACHER"}:
            return True
        return self.id == resource_user_id


def _user_from_token(token: str) -> CurrentUser:
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return CurrentUser(user["id"], user["username"], user["role"])


def extract_ws_token(websocket: WebSocket) -> Optional[str]:
    """Read bearer token from WebSocket subprotocol (preferred) or legacy query param."""
    requested = websocket.headers.get("sec-websocket-protocol", "")
    for proto in requested.split(","):
        candidate = proto.strip()
        if candidate.startswith("bearer."):
            return candidate[len("bearer.") :]
    return websocket.query_params.get("token")


def negotiated_ws_subprotocol(websocket: WebSocket) -> Optional[str]:
    requested = websocket.headers.get("sec-websocket-protocol", "")
    for proto in requested.split(","):
        candidate = proto.strip()
        if candidate.startswith("bearer."):
            return candidate
    return None


def ws_subprotocol_for_token(token: str) -> str:
    return f"bearer.{token}"


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> CurrentUser:
    if credentials:
        return _user_from_token(credentials.credentials)
    raise HTTPException(status_code=401, detail="Authentication required")


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> Optional[CurrentUser]:
    if not credentials:
        return None
    try:
        return _user_from_token(credentials.credentials)
    except HTTPException:
        return None


async def ws_authenticate(websocket: WebSocket) -> CurrentUser:
    token = extract_ws_token(websocket)
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        raise WebSocketDisconnect(code=1008)
    try:
        return _user_from_token(token)
    except HTTPException:
        await websocket.close(code=1008, reason="Invalid or expired token")
        raise WebSocketDisconnect(code=1008) from None


def require_roles(*roles: str):
    async def checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles and user.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return checker
