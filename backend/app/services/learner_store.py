"""Database-backed learner memory (replaces JSON file persistence)."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.db.connection import DEFAULT_MEMORY, db_session

logger = logging.getLogger("tutor.learner_store")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_memory() -> dict[str, Any]:
    return deepcopy(DEFAULT_MEMORY)


class LearnerStore:
    def get_memory(self, user_id: str) -> dict[str, Any]:
        with db_session() as conn:
            row = conn.execute(
                "SELECT data_json FROM learner_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return _empty_memory()
        try:
            data = json.loads(row["data_json"])
            for key, default in DEFAULT_MEMORY.items():
                if key not in data:
                    data[key] = deepcopy(default)
            return data
        except json.JSONDecodeError:
            logger.warning("Corrupt learner profile for %s — resetting.", user_id)
            return _empty_memory()

    def save_memory(self, user_id: str, data: dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False)
        now = _utc_now()
        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO learner_profiles (user_id, data_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at
                """,
                (user_id, payload, now),
            )
        logger.debug("Learner memory persisted for user '%s'.", user_id)

    def migrate_memory(self, from_user_id: str, to_user_id: str) -> None:
        source = self.get_memory(from_user_id)
        if source == _empty_memory():
            return
        target = self.get_memory(to_user_id)
        for concept, value in source.get("mastery", {}).items():
            target["mastery"][concept] = max(target["mastery"].get(concept, 0.0), value)
        target["misconceptions"].update(source.get("misconceptions", {}))
        target["session_history"].extend(source.get("session_history", []))
        self.save_memory(to_user_id, target)
