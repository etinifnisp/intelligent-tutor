"""Local authentication: Argon2 passwords + JWT tokens."""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import (
    JWT_ACCESS_EXPIRE_MINUTES,
    JWT_REFRESH_EXPIRE_DAYS,
    JWT_SECRET,
)
from app.db.connection import db_session

_ph = PasswordHasher()
ROLES = frozenset({"GUEST", "STUDENT", "TEACHER", "ADMIN"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(dt: datetime) -> str:
    return dt.isoformat()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        _ph.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user_id: str, role: str) -> str:
    expire = _utc_now() + timedelta(minutes=JWT_ACCESS_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expire = _utc_now() + timedelta(days=JWT_REFRESH_EXPIRE_DAYS)
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                user_id,
                _hash_token(token),
                _utc_iso(expire),
                _utc_iso(_utc_now()),
            ),
        )
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload


def refresh_access_token(refresh_token: str) -> Optional[dict[str, str]]:
    token_hash = _hash_token(refresh_token)
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT rt.user_id, rt.expires_at, u.role, u.username
            FROM refresh_tokens rt
            JOIN users u ON u.id = rt.user_id
            WHERE rt.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) < _utc_now():
            conn.execute("DELETE FROM refresh_tokens WHERE token_hash = ?", (token_hash,))
            return None
        access = create_access_token(row["user_id"], row["role"])
        return {
            "access_token": access,
            "user": _user_dict(row["user_id"], row["username"], row["role"]),
        }


def _user_dict(user_id: str, username: str, role: str) -> dict[str, str]:
    return {"id": user_id, "username": username, "role": role}


def get_user_by_id(user_id: str) -> Optional[dict[str, str]]:
    with db_session() as conn:
        row = conn.execute(
            "SELECT id, username, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return _user_dict(row["id"], row["username"], row["role"])


def create_guest_user() -> dict[str, Any]:
    user_id = str(uuid.uuid4())
    username = f"guest_{user_id[:8]}"
    now = _utc_iso(_utc_now())
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO users (id, username, password_hash, role, created_at)
            VALUES (?, ?, NULL, 'GUEST', ?)
            """,
            (user_id, username, now),
        )
    return _issue_tokens(user_id, "GUEST", username)


def upgrade_guest_to_student(user_id: str, username: str, password: str) -> Optional[dict[str, Any]]:
    pwd_hash = hash_password(password)
    with db_session() as conn:
        row = conn.execute(
            "SELECT id, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row or row["role"] != "GUEST":
            return None
        try:
            conn.execute(
                """
                UPDATE users
                SET username = ?, password_hash = ?, role = 'STUDENT'
                WHERE id = ?
                """,
                (username, pwd_hash, user_id),
            )
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                return None
            raise
    return _issue_tokens(user_id, "STUDENT", username)


def register_user(
    username: str,
    password: str,
    role: str = "STUDENT",
    migrate_from_user_id: Optional[str] = None,
) -> dict[str, Any]:
    if role not in ROLES or role == "GUEST":
        role = "STUDENT"
    user_id = str(uuid.uuid4())
    now = _utc_iso(_utc_now())
    pwd_hash = hash_password(password)
    with db_session() as conn:
        try:
            conn.execute(
                """
                INSERT INTO users (id, username, password_hash, role, created_at, upgraded_from)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, pwd_hash, role, now, migrate_from_user_id),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("username_taken") from exc
    return _issue_tokens(user_id, role, username)


def login_user(username: str, password: str) -> Optional[dict[str, Any]]:
    with db_session() as conn:
        row = conn.execute(
            "SELECT id, username, role, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if not row or not row["password_hash"]:
        return None
    if not verify_password(row["password_hash"], password):
        return None
    return _issue_tokens(row["id"], row["role"], row["username"])


def _issue_tokens(user_id: str, role: str, username: str) -> dict[str, Any]:
    return {
        "access_token": create_access_token(user_id, role),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
        "user": _user_dict(user_id, username, role),
    }


DEMO_USER_ID = "00000000-0000-4000-8000-000000000001"


def ensure_demo_user() -> dict[str, str]:
    """Create a fixed demo student used when auth is disabled."""
    with db_session() as conn:
        row = conn.execute(
            "SELECT id, username, role FROM users WHERE id = ?",
            (DEMO_USER_ID,),
        ).fetchone()
        if row:
            return _user_dict(row["id"], row["username"], row["role"])
        conn.execute(
            """
            INSERT INTO users (id, username, password_hash, role, created_at)
            VALUES (?, 'Student', NULL, 'STUDENT', ?)
            """,
            (DEMO_USER_ID, _utc_iso(_utc_now())),
        )
    return _user_dict(DEMO_USER_ID, "Student", "STUDENT")


def get_demo_user() -> dict[str, str]:
    user = get_user_by_id(DEMO_USER_ID)
    if user:
        return user
    return ensure_demo_user()


def ensure_admin_user() -> None:
    """Create default admin if none exists (local demo)."""
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    with db_session() as conn:
        row = conn.execute("SELECT id FROM users WHERE role = 'ADMIN' LIMIT 1").fetchone()
        if row:
            return
        user_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO users (id, username, password_hash, role, created_at)
            VALUES (?, ?, ?, 'ADMIN', ?)
            """,
            (user_id, admin_user, hash_password(admin_pass), _utc_iso(_utc_now())),
        )
