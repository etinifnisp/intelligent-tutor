from typing import List, Optional

from pydantic import BaseModel, Field


class ChatPayload(BaseModel):
    session_id: Optional[str] = None  # deprecated — server uses authenticated user id
    student_message: str
    question_id: Optional[str] = None
    chapter_context: Optional[str] = None
    chat_history: List[dict] = []
    confidence_before: Optional[float] = None
    response_time_ms: Optional[int] = None


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    migrate_from_user_id: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class GuestConvertRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: str
    username: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
