"""Conversation, message, and attempt persistence."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.db.connection import db_session


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationStore:
    def get_or_create(self, user_id: str, question_id: Optional[str] = None) -> str:
        with db_session() as conn:
            row = conn.execute(
                """
                SELECT id FROM conversations
                WHERE user_id = ? AND question_id IS ?
                ORDER BY updated_at DESC LIMIT 1
                """,
                (user_id, question_id),
            ).fetchone()
            if row:
                return row["id"]
            conv_id = str(uuid.uuid4())
            now = _utc_now()
            conn.execute(
                """
                INSERT INTO conversations (id, user_id, question_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conv_id, user_id, question_id, now, now),
            )
            return conv_id

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        *,
        model_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
        verification_status: Optional[str] = None,
    ) -> None:
        now = _utc_now()
        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    conversation_id, role, content, model_name, prompt_version,
                    verification_status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    content,
                    model_name,
                    prompt_version,
                    verification_status,
                    now,
                ),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )

    def record_attempt(
        self,
        user_id: str,
        question_id: str,
        answer: Optional[str] = None,
        is_correct: Optional[bool] = None,
        confidence: Optional[float] = None,
        *,
        hints_used: int = 0,
        max_hint_level: int = 0,
        response_time_ms: Optional[int] = None,
        solution_revealed: bool = False,
        concept_ids: Optional[list[str]] = None,
        misconception_type: Optional[str] = None,
    ) -> None:
        import json as _json

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO attempts (
                    user_id, question_id, answer, is_correct, confidence,
                    hints_used, max_hint_level, response_time_ms, solution_revealed,
                    concept_ids, misconception_type, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    question_id,
                    answer,
                    None if is_correct is None else int(is_correct),
                    confidence,
                    hints_used,
                    max_hint_level,
                    response_time_ms,
                    int(solution_revealed),
                    _json.dumps(concept_ids or []),
                    misconception_type,
                    _utc_now(),
                ),
            )

    def get_recent_mistakes(self, user_id: str, *, limit: int = 30) -> list[dict[str, Any]]:
        with db_session() as conn:
            rows = conn.execute(
                """
                SELECT id, question_id, answer, confidence, hints_used, max_hint_level,
                       response_time_ms, misconception_type, concept_ids, created_at
                FROM attempts
                WHERE user_id = ? AND is_correct = 0
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            raw_concepts = item.pop("concept_ids", None)
            if raw_concepts:
                try:
                    item["concept_ids"] = json.loads(raw_concepts)
                except (json.JSONDecodeError, TypeError):
                    item["concept_ids"] = []
            else:
                item["concept_ids"] = []
            results.append(item)
        return results

    def get_progress_metrics(self, user_id: str) -> dict[str, Any]:
        with db_session() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_attempts,
                    SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct_attempts,
                    SUM(CASE WHEN is_correct = 1 AND hints_used = 0 THEN 1 ELSE 0 END)
                        AS correct_without_hints,
                    AVG(CASE WHEN response_time_ms IS NOT NULL THEN response_time_ms END)
                        AS avg_response_time_ms
                FROM attempts
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            recent = conn.execute(
                """
                SELECT is_correct, hints_used, response_time_ms, created_at
                FROM attempts
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (user_id,),
            ).fetchall()

        total = int(totals["total_attempts"] or 0)
        correct = int(totals["correct_attempts"] or 0)
        correct_no_hints = int(totals["correct_without_hints"] or 0)
        avg_ms = totals["avg_response_time_ms"]

        recent_correct = sum(1 for r in recent[:10] if r["is_correct"] == 1)
        older_correct = sum(1 for r in recent[10:] if r["is_correct"] == 1)
        recent_n = min(10, len(recent))
        older_n = max(0, len(recent) - 10)

        return {
            "total_attempts": total,
            "accuracy": round(correct / total, 3) if total else 0.0,
            "accuracy_without_hints": round(correct_no_hints / total, 3) if total else 0.0,
            "avg_response_time_ms": int(avg_ms) if avg_ms is not None else None,
            "recent_accuracy": round(recent_correct / recent_n, 3) if recent_n else None,
            "prior_accuracy": round(older_correct / older_n, 3) if older_n else None,
            "improvement_delta": (
                round((recent_correct / recent_n) - (older_correct / older_n), 3)
                if recent_n and older_n
                else None
            ),
        }
