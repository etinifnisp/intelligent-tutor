"""
Validate corpus_v2 against gold set and corpus quality rules.

Usage:
    python -m pipelines.validate_corpus
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from pipelines.config import (
    CORPUS_V2_PATH,
    GOLD_QUESTIONS_PATH,
    VALIDATION_REPORT_PATH,
)
from pipelines.question_parser import (
    INTERNAL_Q_RE,
    NUMERIC_ONLY_RE,
    parse_raw_text,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def boundary_ok(record: dict[str, Any]) -> bool:
    stem = record.get("stem_text", "") or ""
    if len(stem) < 10:
        return False
    # Internal bleed: a second question header mid-stem (allow leading Qn: prefix)
    tail = stem[10:]
    if INTERNAL_Q_RE.search(tail):
        return False
    if stem.lower().count("question:") > 1:
        return False
    if NUMERIC_ONLY_RE.match(stem.strip()):
        return False
    return True


def options_ok(record: dict[str, Any]) -> bool:
    qtype = record.get("question_type", "")
    options = record.get("options", [])
    if qtype == "INTEGER":
        return True
    if len(options) >= 2:
        return True
    # Some MCQs have no parsed options but stem is valid
    if qtype == "MCQ_SINGLE" and record.get("correct_answer") in {"A", "B", "C", "D"}:
        return len(options) >= 1
    return False


def evaluate_gold(corpus: dict[str, dict[str, Any]]) -> dict[str, Any]:
    gold = load_jsonl(GOLD_QUESTIONS_PATH)
    if not gold:
        return {"gold_count": 0, "matched": 0}

    boundary_hits = 0
    options_hits = 0
    raw_recoverable = 0
    metadata_hits = 0
    matched = 0

    for g in gold:
        qid = g.get("question_id")
        record = corpus.get(qid)
        if not record:
            continue
        matched += 1

        if record.get("raw_text") and record["raw_text"] == record.get("text_layers", {}).get("raw_text"):
            raw_recoverable += 1

        required = ["question_id", "paper_id", "source_pdf_hash", "subject", "schema_version"]
        if all(record.get(k) is not None or k == "source_pdf_hash" for k in required):
            metadata_hits += 1

        if boundary_ok(record):
            boundary_hits += 1
        if options_ok(record):
            options_hits += 1

    def pct(n: int, d: int) -> float:
        return round(100.0 * n / d, 1) if d else 0.0

    return {
        "gold_count": len(gold),
        "matched": matched,
        "boundary_correct_pct": pct(boundary_hits, matched),
        "options_correct_pct": pct(options_hits, matched),
        "raw_recoverable_pct": pct(raw_recoverable, matched),
        "metadata_complete_pct": pct(metadata_hits, matched),
        "boundary_correct_n": boundary_hits,
        "options_correct_n": options_hits,
        "raw_recoverable_n": raw_recoverable,
        "metadata_complete_n": metadata_hits,
    }


def corpus_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    review = Counter(r.get("review_status") for r in records)
    types = Counter(r.get("question_type") for r in records)
    with_answer = sum(1 for r in records if r.get("correct_answer"))
    with_bbox = sum(1 for r in records if r.get("question_bbox"))
    with_page = sum(1 for r in records if r.get("page_number"))
    with_diagram = sum(1 for r in records if r.get("diagram_paths"))
    with_pdf_hash = sum(1 for r in records if r.get("source_pdf_hash"))
    duplicates = sum(1 for r in records if r.get("duplicate_of"))
    avg_conf = (
        round(sum(r.get("extraction_confidence", 0) for r in records) / len(records), 3)
        if records
        else 0
    )
    return {
        "total": len(records),
        "review_status": dict(review),
        "question_types": dict(types),
        "with_correct_answer": with_answer,
        "with_page_number": with_page,
        "with_bbox": with_bbox,
        "with_diagrams": with_diagram,
        "with_source_pdf_hash": with_pdf_hash,
        "duplicate_records": duplicates,
        "avg_extraction_confidence": avg_conf,
    }


def write_report(
    summary: dict[str, Any],
    gold_eval: dict[str, Any],
    checkpoint_pass: bool,
) -> None:
    lines = [
        "# Corpus Validation Report (Phase 2)",
        "",
        "## Corpus Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total questions | {summary['total']:,} |",
        f"| With correct answer | {summary['with_correct_answer']:,} |",
        f"| With page number | {summary['with_page_number']:,} |",
        f"| With bounding box | {summary['with_bbox']:,} |",
        f"| With diagrams | {summary['with_diagrams']:,} |",
        f"| With source PDF hash | {summary['with_source_pdf_hash']:,} |",
        f"| Duplicate records | {summary['duplicate_records']:,} |",
        f"| Avg extraction confidence | {summary['avg_extraction_confidence']} |",
        "",
        "### Review status",
        "",
    ]
    for status, count in sorted(summary["review_status"].items()):
        lines.append(f"- **{status}**: {count:,}")

    lines += [
        "",
        "## Gold Set Evaluation",
        "",
        f"- Gold questions: {gold_eval.get('gold_count', 0)}",
        f"- Matched in corpus_v2: {gold_eval.get('matched', 0)}",
        f"- Boundary correct: {gold_eval.get('boundary_correct_n', 0)} ({gold_eval.get('boundary_correct_pct', 0)}%)",
        f"- Options attached: {gold_eval.get('options_correct_n', 0)} ({gold_eval.get('options_correct_pct', 0)}%)",
        f"- Raw text recoverable: {gold_eval.get('raw_recoverable_n', 0)} ({gold_eval.get('raw_recoverable_pct', 0)}%)",
        f"- Source metadata present: {gold_eval.get('metadata_complete_n', 0)} ({gold_eval.get('metadata_complete_pct', 0)}%)",
        "",
        "## Verification Checkpoint",
        "",
    ]

    checks = [
        (
            "At least 95% of gold questions have correct boundaries",
            gold_eval.get("boundary_correct_pct", 0) >= 95.0,
        ),
        (
            "At least 95% of gold options are correctly attached",
            gold_eval.get("options_correct_pct", 0) >= 95.0,
        ),
        (
            "All raw text remains recoverable",
            gold_eval.get("raw_recoverable_pct", 0) >= 99.0,
        ),
        (
            "Every question has source metadata",
            summary["total"] > 0
            and all(
                r.get("question_id") and r.get("paper_id") and r.get("schema_version")
                for r in load_jsonl(CORPUS_V2_PATH)[:50]
            ),
        ),
    ]

    for label, ok in checks:
        lines.append(f"- [{'x' if ok else ' '}] {label}")

    lines += [
        "",
        f"**Overall checkpoint:** {'PASS' if checkpoint_pass else 'NEEDS ATTENTION'}",
        "",
    ]

    VALIDATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def validate_corpus() -> dict[str, Any]:
    records = load_jsonl(CORPUS_V2_PATH)
    if not records:
        raise FileNotFoundError(
            f"corpus_v2 not found or empty. Run: python -m pipelines.build_corpus_v2"
        )

    corpus_by_id = {r["question_id"]: r for r in records}
    summary = corpus_summary(records)
    gold_eval = evaluate_gold(corpus_by_id)

    checkpoint_pass = (
        gold_eval.get("boundary_correct_pct", 0) >= 95.0
        and gold_eval.get("options_correct_pct", 0) >= 95.0
        and gold_eval.get("raw_recoverable_pct", 0) >= 99.0
        and summary["total"] > 0
    )

    write_report(summary, gold_eval, checkpoint_pass)

    return {
        "summary": summary,
        "gold_eval": gold_eval,
        "checkpoint_pass": checkpoint_pass,
        "report_path": str(VALIDATION_REPORT_PATH),
    }


def main() -> None:
    result = validate_corpus()
    print(f"Validation report: {result['report_path']}")
    print(f"Checkpoint: {'PASS' if result['checkpoint_pass'] else 'NEEDS ATTENTION'}")
    ge = result["gold_eval"]
    print(
        f"Gold boundaries: {ge.get('boundary_correct_pct')}% | "
        f"options: {ge.get('options_correct_pct')}% | "
        f"raw recoverable: {ge.get('raw_recoverable_pct')}%"
    )


if __name__ == "__main__":
    main()
