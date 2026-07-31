"""Verification benchmark — gold-set tool coverage report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import CORPUS_V2_PATH, EVAL_DIR, GOLD_QUESTIONS_PATH  # noqa: E402
from app.verification.answer_checker import get_official_answer, verify_student_answer  # noqa: E402
from app.verification.schemas import VerificationStatus  # noqa: E402


def evaluate() -> dict:
    corpus: dict = {}
    with open(CORPUS_V2_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                corpus[row["question_id"]] = row

    total = 0
    with_key = 0
    tool_checked = 0
    verified = 0
    failures = 0

    with open(GOLD_QUESTIONS_PATH, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            g = json.loads(line)
            total += 1
            q = corpus.get(g["question_id"], g)
            official = get_official_answer(q)
            if not official:
                continue
            with_key += 1
            msg = (
                f"My answer is {official}"
                if g.get("category") == "integer" or str(official).isdigit()
                else f"Is option {official} correct?"
            )
            report = verify_student_answer(msg, q)
            if report.tool_calls:
                tool_checked += 1
            if report.status == VerificationStatus.VERIFIED:
                verified += 1
            if report.status == VerificationStatus.TOOL_FAILURE:
                failures += 1

    coverage = tool_checked / with_key if with_key else 0.0
    report = {
        "gold_total": total,
        "with_answer_key": with_key,
        "tool_checked": tool_checked,
        "verified": verified,
        "tool_failures": failures,
        "tool_coverage": round(coverage, 4),
        "checkpoint_pass": coverage >= 0.95 and failures == 0,
    }
    out = EVAL_DIR / "verification_eval_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Tool coverage: {coverage:.1%} ({tool_checked}/{with_key}) | "
        f"PASS: {report['checkpoint_pass']}"
    )
    print(f"Report: {out}")
    return report


if __name__ == "__main__":
    evaluate()
