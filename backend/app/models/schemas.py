from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.config import MAX_MESSAGE_LENGTH


class ChatPayload(BaseModel):
    session_id: Optional[str] = None  # deprecated — server uses authenticated user id
    student_message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    question_id: Optional[str] = Field(default=None, max_length=128)
    chapter_context: Optional[str] = Field(default=None, max_length=256)
    chat_history: List[dict] = Field(default_factory=list, max_length=20)

    @field_validator("chat_history")
    @classmethod
    def validate_chat_history(cls, value: List[dict]) -> List[dict]:
        for item in value:
            role = item.get("role")
            content = item.get("content")
            if role not in {"user", "model", "assistant"}:
                raise ValueError("Invalid chat history role")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Invalid chat history content")
            if len(content) > MAX_MESSAGE_LENGTH:
                raise ValueError("Chat history entry too long")
        return value
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
