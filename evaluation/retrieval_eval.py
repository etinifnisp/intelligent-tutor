"""Retrieval benchmark from gold questions + Recall@5 evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import EVAL_DIR, GOLD_QUESTIONS_PATH, RETRIEVAL_BENCHMARK_PATH  # noqa: E402
from app.retrieval.service import RetrievalService  # noqa: E402


def build_benchmark() -> int:
    gold_path = GOLD_QUESTIONS_PATH
    if not gold_path.exists():
        print("Gold questions not found.")
        return 0
    count = 0
    RETRIEVAL_BENCHMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(gold_path, "r", encoding="utf-8") as fin, open(
        RETRIEVAL_BENCHMARK_PATH, "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            if not line.strip():
                continue
            g = json.loads(line)
            stem = g.get("raw_text") or ""
            query = stem[:200] if stem else g.get("chapter", "")
            row = {
                "query": query,
                "expected_question_id": g["question_id"],
                "subject": g.get("subject"),
                "chapter": g.get("chapter"),
            }
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    print(f"Wrote {count} benchmark queries -> {RETRIEVAL_BENCHMARK_PATH}")
    return count


def evaluate(recall_k: int = 5) -> dict:
    if not RETRIEVAL_BENCHMARK_PATH.exists():
        build_benchmark()
    svc = RetrievalService()
    if not svc.load():
        raise RuntimeError("Retrieval indexes not built")

    hits = 0
    total = 0
    mrr_sum = 0.0
    with open(RETRIEVAL_BENCHMARK_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            results = svc.search(
                row["query"],
                subject=row.get("subject"),
                chapter=row.get("chapter"),
                top_k=recall_k,
            )
            ids = [r["question_id"] for r in results]
            expected = row["expected_question_id"]
            total += 1
            if expected in ids:
                hits += 1
                mrr_sum += 1.0 / (ids.index(expected) + 1)

    recall = hits / total if total else 0.0
    mrr = mrr_sum / total if total else 0.0
    report = {
        "total": total,
        "recall_at_5": round(recall, 4),
        "mrr": round(mrr, 4),
        "checkpoint_pass": recall >= 0.90,
    }
    out = EVAL_DIR / "retrieval_eval_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Recall@{recall_k}: {recall:.1%} | MRR: {mrr:.3f} | PASS: {report['checkpoint_pass']}")
    print(f"Report: {out}")
    return report


if __name__ == "__main__":
    evaluate()
