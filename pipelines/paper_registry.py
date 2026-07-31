"""Track per-paper PDF hashes for incremental reprocessing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipelines.pdf_enricher import find_pdf_for_paper, sha256_file


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"papers": {}, "updated_at": None}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_registry(path: Path, registry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    registry["updated_at"] = _utc_now()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


def paper_needs_reprocess(
    registry: dict[str, Any],
    paper_filename: str,
    papers_dir: Path,
    force: bool = False,
) -> tuple[bool, dict[str, Any]]:
    meta = registry.get("papers", {}).get(paper_filename, {})
    pdf_path = find_pdf_for_paper(papers_dir, paper_filename)
    pdf_hash = sha256_file(pdf_path) if pdf_path else None

    info = {
        "paper_filename": paper_filename,
        "pdf_path": str(pdf_path) if pdf_path else None,
        "pdf_hash": pdf_hash,
        "last_processed_at": meta.get("last_processed_at"),
    }

    if force:
        return True, info
    if not meta:
        return True, info
    if pdf_hash and meta.get("pdf_hash") != pdf_hash:
        return True, info
    if not meta.get("processed_v2"):
        return True, info
    return False, info


def mark_paper_processed(
    registry: dict[str, Any],
    paper_filename: str,
    pdf_hash: str | None,
    question_count: int,
) -> None:
    registry.setdefault("papers", {})[paper_filename] = {
        "pdf_hash": pdf_hash,
        "processed_v2": True,
        "question_count": question_count,
        "last_processed_at": _utc_now(),
    }
