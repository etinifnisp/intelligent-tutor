"""SQLite database backup and restore."""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import DATABASE_PATH, PROJECT_ROOT  # noqa: E402

BACKUP_DIR = PROJECT_ROOT / "data" / "backups"


def backup(dest: Path | None = None) -> Path:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = dest or (BACKUP_DIR / f"app_{stamp}.db")
    shutil.copy2(DATABASE_PATH, target)
    print(f"Backup written: {target}")
    return target


def restore(source: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Backup not found: {source}")
    if DATABASE_PATH.exists():
        pre = BACKUP_DIR / f"pre_restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.db"
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DATABASE_PATH, pre)
        print(f"Pre-restore safety copy: {pre}")
    shutil.copy2(source, DATABASE_PATH)
    print(f"Restored database from: {source}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup or restore SQLite database")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backup", help="Create timestamped backup")
    p_restore = sub.add_parser("restore", help="Restore from backup file")
    p_restore.add_argument("file", type=Path, help="Path to backup .db file")
    args = parser.parse_args()

    if args.cmd == "backup":
        backup()
        return 0
    restore(args.file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
