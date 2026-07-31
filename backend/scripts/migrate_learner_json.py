"""One-time migration: legacy learner_memory.json -> SQLite."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.config import LEARNER_MEMORY_PATH  # noqa: E402
from app.db import init_database  # noqa: E402
from app.db.connection import db_session  # noqa: E402
from app.services.learner_store import LearnerStore  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def migrate() -> None:
    if not LEARNER_MEMORY_PATH.exists():
        print("No legacy learner_memory.json found — nothing to migrate.")
        return

    init_database()
    with open(LEARNER_MEMORY_PATH, "r", encoding="utf-8") as f:
        legacy = json.load(f)

    store = LearnerStore()
    migrated = 0
    for session_id, data in legacy.items():
        user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"legacy-session:{session_id}"))
        username = f"legacy_{session_id[:24]}"
        with db_session() as conn:
            exists = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
            if not exists:
                conn.execute(
                    """
                    INSERT INTO users (id, username, password_hash, role, created_at)
                    VALUES (?, ?, NULL, 'GUEST', ?)
                    """,
                    (user_id, username, _utc_now()),
                )
        store.save_memory(user_id, data)
        migrated += 1
        print(f"  migrated session '{session_id}' -> user {user_id}")

    print(f"Migrated {migrated} legacy session(s) into SQLite.")


if __name__ == "__main__":
    migrate()
