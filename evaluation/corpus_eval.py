"""Corpus quality evaluation — summary metrics and checkpoint."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import CORPUS_PATH, CORPUS_V2_PATH, EVAL_DIR, GOLD_QUESTIONS_PATH  # noqa: E402


def evaluate() -> dict:
    report: dict = {"corpus_v1": {}, "corpus_v2": {}, "gold_set": {}}

    if CORPUS_PATH.exists():
        with open(CORPUS_PATH, encoding="utf-8") as f:
            v1 = json.load(f)
        subjects = Counter(q.get("subject", "Unknown") for q in v1)
        with_answer = sum(1 for q in v1 if q.get("correct_answer"))
        report["corpus_v1"] = {
            "total": len(v1),
            "subjects": dict(subjects),
            "with_correct_answer": with_answer,
            "answer_coverage": round(with_answer / len(v1), 4) if v1 else 0.0,
        }

    if CORPUS_V2_PATH.exists():
        v2_rows = []
        with open(CORPUS_V2_PATH, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    v2_rows.append(json.loads(line))
        reviewed = sum(1 for r in v2_rows if r.get("review_status") == "REVIEWED")
        with_key = sum(1 for r in v2_rows if r.get("correct_answer"))
        report["corpus_v2"] = {
            "total": len(v2_rows),
            "reviewed": reviewed,
            "with_correct_answer": with_key,
            "review_coverage": round(reviewed / len(v2_rows), 4) if v2_rows else 0.0,
        }

    gold_total = 0
    if GOLD_QUESTIONS_PATH.exists():
        with open(GOLD_QUESTIONS_PATH, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    gold_total += 1
    report["gold_set"] = {"total": gold_total}

    report["checkpoint_pass"] = (
        report.get("corpus_v1", {}).get("total", 0) > 0 and gold_total >= 50
    )

    out = EVAL_DIR / "corpus_eval_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Corpus eval: v1={report.get('corpus_v1', {}).get('total', 0)} gold={gold_total}")
    print(f"PASS: {report['checkpoint_pass']}")
    print(f"Report: {out}")
    return report


if __name__ == "__main__":
    evaluate()
