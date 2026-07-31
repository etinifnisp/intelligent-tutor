"""Database backup and restore tests."""

from __future__ import annotations

import sqlite3

from scripts import backup_db


def test_backup_and_restore_roundtrip(tmp_path, monkeypatch):
    database_path = tmp_path / "app.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE attempts (id TEXT PRIMARY KEY)")
    monkeypatch.setattr(backup_db, "DATABASE_PATH", database_path)
    monkeypatch.setattr(backup_db, "BACKUP_DIR", tmp_path / "backups")

    dest = tmp_path / "roundtrip.db"
    backup_db.backup(dest)
    assert dest.exists()

    conn = sqlite3.connect(str(dest))
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "users" in tables
    assert "attempts" in tables

    backup_db.restore(dest)
    assert database_path.exists()
